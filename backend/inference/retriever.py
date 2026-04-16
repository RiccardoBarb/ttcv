from backend.data_pipeline import indexers
from backend.utils.embedding import embed_fn
from faiss import normalize_L2
import numpy as np
import Stemmer
import bm25s
import yaml

class Retriever:

    def __init__(self,cfg):
        self.data_dir = cfg['data_dir']
        self.embedding_model_params = cfg['embedding']
        self.chunks = indexers.load_or_create_chunks(self.data_dir)
        self.sparse_index = indexers.load_or_create_sparse_index(self.data_dir)
        self.dense_index = indexers.load_or_create_dense_index(self.data_dir,self.embedding_model_params)

    def reconstruct_docs(self,results):
        docs = {}
        context = ''
        metadata = [(self.chunks[i]['source'], self.chunks[i]['chunk_id'], self.chunks[i]['heading'], self.chunks[i]['parent'])
                    for i in results[0]]
        #first we get the unique sources
        for src in list(dict.fromkeys(i[0] for i in metadata)):
            if src not in docs:
                docs[src] = {}
            #for each source we get the preamble if present to give generic context
            preamble_id = [i['chunk_id'] for i in self.chunks if (i['heading']=='preamble')&(i['source']==src)]
            if preamble_id:
                preamble_content = [i['content'] for i in self.chunks if (i['source']==src)&(i['chunk_id']==preamble_id[0])]
                docs[src]['preamble'] = preamble_content[0]
            #then we get the parent
            for parent in list(dict.fromkeys(i[3] for i in metadata)):
                if (parent not in docs[src]) & (parent != ''):
                    parent_id = [i['chunk_id'] for i in self.chunks if (i['heading'] == parent) & (i['source'] == src)]
                    if parent_id:
                        parent_content = [i['content'] for i in self.chunks if (i['source'] == src) & (i['chunk_id'] == parent_id[0])]
                        docs[src][parent] = parent_content[0]
            #finally the heading is not already included in parent or preamble
            for heading in list(dict.fromkeys(i[2] for i in metadata)):
                if heading not in docs[src]:
                    heading_id = [i['chunk_id'] for i in self.chunks if (i['heading'] == heading) & (i['source'] == src)]
                    if heading_id:
                        heading_content = [i['content'] for i in self.chunks if (i['source'] == src) & (i['chunk_id'] == heading_id[0])]
                        docs[src][heading] = heading_content[0]
        for src,doc_content in docs.items():
            context+=f'---{src}---\n\n'
            for heading,content in doc_content.items():
                if heading in list(dict.fromkeys(i[3] for i in metadata)):
                    context+=f'## {heading}\n'
                else:
                    context+=f'### {heading}\n'
                context+=f'{content}\n'

        return docs,context

    def dense_retrieval(self,query,k=2):
        query = self.embedding_model_params.get('retrieval_instructions','')+query #embedding models like qwen3 accept embedding instructions
        q_emb = embed_fn([query],self.embedding_model_params)[0]
        q_emb = np.array([q_emb]).astype("float32")
        normalize_L2(q_emb)
        similarities, indices = self.dense_index.search(q_emb, k)
        return indices,q_emb

    def sparse_retrieval(self,query,k=2):
        stemmer = Stemmer.Stemmer("english")
        tokens = bm25s.tokenize(query, stemmer = stemmer)
        results, scores = self.sparse_index.retrieve(tokens, k=k, sorted=True)
        return results

    def rerank(self,q_emb,results,top_k=2):
        vectors = np.empty([results.shape[1],self.dense_index.d],np.float32)
        for i,j in enumerate(results[0]):
            vectors[i,:] = self.dense_index.reconstruct(int(j))

        scores = np.dot(vectors,q_emb.T).squeeze()
        top_k_scores = scores[:top_k]
        candidates = results[0][np.argsort(-scores)].reshape(1,len(scores))

        return candidates


if __name__=='__main__':
    with open("backend/cfg.yml", "r") as c:
        cfg = yaml.load(c, Loader=yaml.SafeLoader)
    top_k_dense = cfg['retrieval']['top_k_dense']
    top_k_sparse = cfg['retrieval']['top_k_sparse']
    top_k_reranked = cfg['retrieval']['top_k_reranked']
    q = "test query"
    r = Retriever(cfg)
    results_s = r.sparse_retrieval(q,top_k_sparse)
    results_d,q_emb = r.dense_retrieval(q,top_k_dense)
    results = np.unique(np.hstack([results_d,results_s])).reshape(1,-1)
    reranked_results = r.rerank(q_emb,results,top_k_reranked)
    docs,out=r.reconstruct_docs(reranked_results)
    print(out)