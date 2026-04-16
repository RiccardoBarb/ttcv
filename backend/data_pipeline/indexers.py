from backend.data_pipeline.chunking import parse_md_to_chunks
from backend.utils.embedding import embed_fn
import numpy as np
import bm25s
import Stemmer
import faiss
import pickle
import yaml
import os
from dotenv import load_dotenv
load_dotenv()

def load_or_create_chunks(data_dir : str, overwrite: bool = False):
    path = os.path.join(data_dir, "chunks.pkl")
    if os.path.exists(path) and not overwrite:
        with open(path, "rb") as f:
            return pickle.load(f)
    chunks = []
    for source in os.listdir(data_dir):
        if source.endswith(".md"):
            source_path = os.path.join(data_dir, source)
            chunks.extend(parse_md_to_chunks(source_path, source))
    # update id with len of entire kb
    for i,v in enumerate(chunks):
        v.update({'chunk_id':i})
    with open(path, "wb") as f:
        pickle.dump(chunks, f)

    return chunks

def load_or_create_sparse_index(data_dir: str, chunks: list | None = None, overwrite: bool = False):
    path = os.path.join(data_dir, "bm25.pkl")
    if os.path.exists(path) and not overwrite:
        print("Loading existing BM25 index...")
        with open(path, "rb") as f:
            return pickle.load(f)
    if chunks is None:
        chunks = load_or_create_chunks(data_dir)
    corpus = [c["content"] for c in chunks]
    stemmer = Stemmer.Stemmer("english")
    tokenized = bm25s.tokenize(corpus, stopwords = "en", stemmer = stemmer)
    sparse_indexer = bm25s.BM25()
    sparse_indexer.index(tokenized)
    with open(path, "wb") as f:
        pickle.dump(sparse_indexer, f)

    return sparse_indexer

def load_or_create_dense_index(data_dir,model_params:dict, chunks: list | None = None, overwrite: bool = False):

    index_path = os.path.join(data_dir, "faiss.index")

    if os.path.exists(index_path) and not overwrite:
        index = faiss.read_index(index_path)
        return index

    if chunks is None:
        chunks = load_or_create_chunks(data_dir)

    bias = model_params.get('encoding_instructions','') #embedding models like qwen3 can receive embedding instructions
    corpus = [bias+c["content"] for c in chunks]

    embeddings = embed_fn(corpus,model_params)  # shape: (N, dim)
    embeddings = np.array(embeddings).astype("float32")
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(embeddings)  # in-place L2 normalization
    index.add(embeddings)
    faiss.write_index(index, index_path)

    return index

if __name__=='__main__':
    with open("backend/cfg.yml", "r") as c:
        cfg = yaml.load(c, Loader=yaml.SafeLoader)

    data_dir = cfg.get('data_dir')
    chunks = load_or_create_chunks(data_dir)
    load_or_create_sparse_index(data_dir,chunks)
    load_or_create_dense_index(data_dir,cfg['embedding'],chunks)