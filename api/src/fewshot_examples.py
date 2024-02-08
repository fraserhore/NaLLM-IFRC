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
MATCH (p:ResearchProject)-[:INCLUDES]-(c:Country {{iso3: "UGA"}}) RETURN p.project_title AS project_title
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
Question: What is the biggest disaster in living memory?
Cypher:
CALL apoc.ml.openai.embedding(["What is the biggest disaster in living memory?"], 
   "{openai_api_key}") YIELD embedding
MATCH (c:Chunk)
WHERE c.embedding
WITH c, gds.similarity.cosine(c.embedding, embedding) AS score
ORDER BY score DESC LIMIT 3
RETURN c.text, score
Question: What are the key lessons related to ensuring preparedness and resilient communities?
Cypher:
CALL apoc.ml.openai.embedding(["What are the key lessons related to ensuring preparedness and resilient communities?"], 
   "{openai_api_key}") YIELD embedding
CALL db.index.vector.queryNodes('lesson-embeddings', 10, embedding)
YIELD node AS lesson, score
RETURN lesson.excerpt, score

IMPORTANT TIPS:
When matching country nodes, use the country iso3 property and not the country name property. For example, to match the country node for Uganda, use the following Cypher statement:
```MATCH (c:Country {{iso3: 'UGA'}}) RETURN c```.
When searching for specific information in text chunks, never use the CONTAINS clause, always use the apoc.ml.openai.embedding and gds.similarity.cosine functions as shown in the examples.
When returning text chunks, always return exactly three chunks, no more, no less, always return the chunks with the highest cosine similarity score, always return the chunks in descending order of cosine similarity score, and always return the chunks that have a cosine similarity score of at least 0.5.

"""
