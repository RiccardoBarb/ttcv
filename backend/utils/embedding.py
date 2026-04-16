from openai import OpenAI
import os

def embed_fn(texts,params):
    # instantiate client
    client = OpenAI(base_url=os.environ['EMBEDDING_URL'],api_key=os.environ['EMBEDDING_KEY'])
    response = client.embeddings.create(model=params['model'],dimensions=params['dimensions'],input=texts)
    return [d.embedding for d in response.data]