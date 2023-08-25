def get_fewshot_examples(openai_api_key):
    return f"""
Question: How many National Societies are there?
Cypher:
MATCH (n:NationalSociety)
RETURN count(n) AS numberOfNationalSocieties
Question: How many National Societies are there in Africa?
Cypher:
MATCH (n:NationalSociety)-[:LOCATED_IN]->(:Country)-[:LOCATED_IN*]->(:Region {{name: 'Africa'}})
RETURN count(n) AS numberOfNationalSocieties
Question: Which National Societies have been affected by an earthquake?
Cypher:
MATCH (n:NationalSociety)-[:LOCATED_IN]->(:Country)-[:AFFECTED_BY]->(:Crisis)-[:HAS_DRIVER]->(:Driver {{name: 'Earthquake'}}) 
RETURN DISTINCT n.name AS NationalSociety
Question: Which research projects include Uganda?
Cypher:
MATCH (p:ResearchProject)-[:INCLUDES]-(c:Country {{name: "Uganda"}}) RETURN p.project_title AS project_title
Question: How many lessons are related to both strong winds and coordination with authorities?
Cypher:
MATCH (l:Lesson)-[:RELATED_TO]->(:Hazard {{name: 'Strong Wind'}})
MATCH (l)-[:RELATED_TO]->(:Per_Component {{name: 'Coordination with Authorities'}}) 
RETURN count(l) AS numberOfLessons
Question: What are the core principles of the IFRC?
Cypher:
CALL apoc.ml.openai.embedding(["What are the core principles of the IFRC?"], 
   "{openai_api_key}") YIELD embedding
MATCH (c:Chunk)
WHERE c.embedding
WITH c, gds.similarity.cosine(c.embedding, embedding) AS score
ORDER BY score DESC LIMIT 3
RETURN c.text, score
Question: What is Microsoft policy regarding to the return to office?
Cypher:
CALL apoc.ml.openai.embedding(["What is Microsoft policy regarding to the return to office?"], "{openai_api_key}") YIELD embedding
MATCH (o:Organization {{name:"Microsoft"}})<-[:MENTIONS]-()-[:HAS_CHUNK]->(c)
WHERE c.embedding
WITH distinct c, embedding
WITH c, gds.similarity.cosine(c.embedding, embedding) AS score
ORDER BY score DESC LIMIT 3
RETURN c.text, score

When searching for specific information in the text chunks, never use the CONTAINS clause, but always use the apoc.ml.openai.embedding
and gds.similarity.cosine functions as shown in the examples.
When returning text chunks, always return exactly three chunks, no more, no less.
Remember, instead of using CONTAINS to find information within text chunks use the apoc.ml.openai.embedding and gds.similarity.cosine functions.
"""
