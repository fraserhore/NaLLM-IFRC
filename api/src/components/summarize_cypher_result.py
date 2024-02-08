from typing import Any, Awaitable, Callable, Dict, List

from components.base_component import BaseComponent
from llm.basellm import BaseLLM

system = f"""
Your task is to generate a natural language answer to a given question based on given data.
Do not mention that your answer is based on the given data.
Do not add any additional information that is not explicitly provided in the given data.
I repeat, do not add any information that is not explicitly given.
Make the answer as concise as possible and do not use more than 100 words. 
Use bullet points for lists longer than three items.
"""

def remove_large_lists(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    The idea is to remove all properties that have large lists (embeddings) or text as values
    """
    LIST_CUTOFF = 56
    CHARACTER_CUTOFF = 5000
    # iterate over all key-value pairs in the dictionary
    for key, value in d.items():
        # if the value is a list and has more than list cutoff elements
        if isinstance(value, list) and len(value) > LIST_CUTOFF:
            d[key] = None
        # if the value is a string and has more than list cutoff elements
        if isinstance(value, str) and len(value) > CHARACTER_CUTOFF:
            d[key] = d[key][:CHARACTER_CUTOFF]
        # if the value is a dictionary
        elif isinstance(value, dict):
            # recurse into the nested dictionary
            remove_large_lists(d[key])
    return d


class SummarizeCypherResult(BaseComponent):
    llm: BaseLLM
    exclude_embeddings: bool

    def __init__(self, llm: BaseLLM, exclude_embeddings: bool = True) -> None:
        self.llm = llm
        self.exclude_embeddings = exclude_embeddings

    def generate_user_prompt(self, question: str, results: List[Dict[str, str]]) -> str:
        return f"""
        Answer the question below, delimited by triple backticks.
        Question: ```{question}```
        Answer the question using the following data, delimited by triple backticks.
        Data:
        ```{[remove_large_lists(el) for el in  results] if self.exclude_embeddings else results}```
        """

    def run(
        self,
        question: str,
        results: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": self.generate_user_prompt(question, results)},
        ]

        print(f"Generating summary of cypher results with the following messages:\n\n{messages}\n")

        output = self.llm.generate(messages)

        print(f"LLM response with summary of cypher results:\n{output}\n")

        return output

    async def run_async(
        self,
        question: str,
        results: List[Dict[str, Any]],
        callback: Callable[[str], Awaitable[Any]] = None,
    ) -> Dict[str, str]:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": self.generate_user_prompt(question, results)},
        ]

        print(f"Streaming summary of cypher results with the following messages:\n\n{messages}\n")
        print("LLM streamed response with summary of cypher results:\n")

        output = await self.llm.generateStreaming(messages, onTokenCallback=callback)

        print(output)

        return "".join(output)
