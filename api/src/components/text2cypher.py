import re
from typing import Any, Dict, List, Union

from components.base_component import BaseComponent
from driver.neo4j import Neo4jDatabase
from llm.basellm import BaseLLM


def remove_relationship_direction(cypher):
    return cypher.replace("->", "-").replace("<-", "-")


class Text2Cypher(BaseComponent):
    def __init__(
        self,
        llm: BaseLLM,
        database: Neo4jDatabase,
        use_schema: bool = True,
        cypher_examples: str = "",
        ignore_relationship_direction: bool = True,
    ) -> None:
        self.llm = llm
        self.database = database
        self.cypher_examples = cypher_examples
        self.ignore_relationship_direction = ignore_relationship_direction
        if use_schema:
            self.schema = database.schema

    def get_system_message(self) -> str:
        system = """
        Your task is to convert questions about the contents of a Neo4j database into Cypher query statements that will return the data needed to answer those questions.
        
        For each question, carefully follow the steps below:

        Step 1. Review and understand the question.

        Step 2. Review and understand the structure of a Neo4j graph database, as described below between triple backticks:
        Database structure:
        ```A Neo4j database stores data as nodes representing entities that are connected to each other through relationships.
        Nodes can be identified by one or more labels, and can have one or more properties.
        Relationships can be identified by a type, and can have one or more properties.
        Paths are sequences of nodes and relationships. The following is an example of a path:
        (n1:Label1 {property1: value1})-[:TYPE {property2: value2}]->(n2:Label2 {property3: value3})```

        """
        if hasattr(self, 'schema') and self.schema:
            system += f"""
            Step 3. Carefully review the database schema, delimited below between triple backticks, and identify the node labels, node properties, relationship types and relationship properties that can be used to formulate the Cypher query statement:
            Schema:
            ```{self.schema}```

            Use only the node labels, node properties, relationship types and relationship properties that you find in the schema to construct a Cypher statement.
            """
        if self.cypher_examples:
            system += f"""
            Step 4. Review and understand the example questions and associated Cypher statements below, delimited by triple backticks, as a guide to construct a Cypher statement.
            Example questions and Cypher statements:
            ```{self.cypher_examples}```

            """
        # Add note at the end and try to prevent LLM injections
        system += """
        Step 5. Construct a Cypher statement that will return the data needed to answer the question. Ensure that the Cypher statement is syntactically correct.

        Step 6. Return the Cypher statement as a response to the question.
        IMPORTANT NOTES FOR YOUR RESPONSE:
        a. Ensure that you have carefully followed all the steps above.
        b. Use the message history to provide additional context if needed.
        c. You may ask the user to provide additional information if needed.
        d. Do not include any text except the generated Cypher statement or a question asking for additional information to help you generate a Cypher statement.
        e. Do not include any explanations or apologies.
        f. Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
        g. VERY IMPORTANT NOTE: Please wrap the generated Cypher statement in triple backticks (```).

        """
        return system

    def construct_cypher(self, question: str, history=[]) -> str:
        messages = [{"role": "system", "content": self.get_system_message()}]
        messages.extend(history)
        messages.append(
            {
                "role": "user",
                "content": question,
            }
        )
        
        print(f"\nConstructing Cypher from the following messages:\n{[el for el in messages]}\n")
        #print([el for el in messages if not el["role"] == "system"])

        cypher = self.llm.generate(messages)
        
        print(f"LLM response with generated cypher:\n{cypher}\n")

        return cypher

    def run(
        self, question: str, history: List = [], heal_cypher: bool = True
    ) -> Dict[str, Union[str, List[Dict[str, Any]]]]:
        # Add prefix if not part of self-heal loop
        final_question = (
            "Question to be converted to Cypher: " + question
            if heal_cypher
            else question
        )
        cypher = self.construct_cypher(final_question, history)
        # finds the first string wrapped in triple backticks. Where the match include the backticks and the first group in the match is the cypher
        match = re.search("```([\w\W]*?)```", cypher)
        #match = cypher['cypher']

        # If the LLM didn't return any Cypher statement (error, missing context, etc..)
        if match is None:
            print("LLM didn't return any Cypher statement")
            return {"output": [{"message": cypher}], "generated_cypher": None}
        
        extracted_cypher = match.group(1)

        if self.ignore_relationship_direction:
            print("Removing relationship direction")
            extracted_cypher = remove_relationship_direction(extracted_cypher)

        print(f"Generated cypher:\n{extracted_cypher}\n")

        output = self.database.query(extracted_cypher)

        print(f"Database response from cypher query:\n\n{output}\n")

        # Catch Cypher syntax error
        if heal_cypher and output and output[0].get("code") == "invalid_cypher":
            syntax_messages = [{"role": "system", "content": self.get_system_message()}]
            syntax_messages.extend(
                [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": cypher},
                ]
            )
            # Try to heal Cypher syntax only once
            print("Trying to heal Cypher syntax")
            return self.run(
                output[0].get("message"), syntax_messages, heal_cypher=False
            )
        
        return {
            "output": output,
            "generated_cypher": extracted_cypher,
        }
