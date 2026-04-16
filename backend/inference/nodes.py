from backend.utils import llm, parsing
from pocketflow import Node
import numpy as np
import random
import logging
import re

logger = logging.getLogger(__name__)

class Contextualize(Node):
    def prep(self, shared):
        """Get query, prompts, cfg"""
        hl = shared['cfg']['history_length']
        history = shared.get('history',[])[-hl:]
        return shared["query"], history, shared['prompts'], shared['cfg']

    def exec(self, inputs):
        """Contextualize the question given the history"""
        query, history, prompts, cfg = inputs
        query = re.sub(r'[{}]', '', query)
        char_limit = cfg['query_char_limit']
        answer = f'too many characters in the query - keep the question within {char_limit} characters'
        if len(query)<=char_limit:
            system_prompt = prompts['system']['contextualize']
            user_prompt = prompts['user']['contextualize']
            model_params = cfg['llm']
            system_format_args = {'main_user': cfg['user_info']['main_user']}
            user_format_args = {'user_question': query,'history':history}
            answer = llm.query_llm(system_prompt, user_prompt, system_format_args, user_format_args, model_params)
            answer = parsing.extract_xml(answer, 'question')
        return answer

    def post(self, shared, prep_res, exec_res):
        """Overwrite query with contextualized version and update history"""
        hl = shared['cfg']['history_length']
        history = shared.get('history', [])
        history.append({'query':  shared["query"]})#<-store original query in history
        shared["query"] = exec_res
        shared['history'] = history[-hl:]
        logger.info(f"[Contextualize] {exec_res}")
        return 'default'


class ScopeDetection(Node):
    def prep(self, shared):
        """Get query, prompts, cfg"""
        return shared["query"], shared['prompts'], shared['cfg']

    def exec(self, inputs):
        """Check whether the question is in scope"""
        query, prompts, cfg = inputs
        system_prompt = prompts['system']['scope_detection']
        user_prompt = prompts['user']['scope_detection']
        model_params = cfg['llm']
        system_format_args = {'main_user':cfg['user_info']['main_user']}
        user_format_args = {'user_question':query}
        answer = llm.query_llm(system_prompt,user_prompt,system_format_args,user_format_args,model_params)
        answer = parsing.extract_xml(answer,'relevance')
        return answer

    def post(self, shared, prep_res, exec_res):
        """Store generated answer in shared store"""
        shared["relevance"] = exec_res
        logger.info(f"[ScopeDetection] {exec_res}")
        return exec_res

class QueryRouter(Node):
    def prep(self, shared):
        """Get query, prompts, cfg"""
        return shared["query"], shared['prompts'], shared['cfg']

    def exec(self, inputs):
        """Route question to appropriate retrieval type"""
        query, prompts, cfg = inputs
        system_prompt = prompts['system']['routing']
        user_prompt = prompts['user']['routing']
        model_params = cfg['llm']
        system_format_args = {'main_user':cfg['user_info']['main_user']}
        user_format_args = {'user_question':query}
        answer = llm.query_llm(system_prompt,user_prompt,system_format_args,user_format_args,model_params)
        answer = parsing.extract_xml(answer,'question_type')
        return answer

    def post(self, shared, prep_res, exec_res):
        """Store generated answer in shared store"""
        shared["route"] = exec_res
        logger.info(f"[QueryRouter] {exec_res}")
        return exec_res

class DocumentClassification(Node):
    def prep(self, shared):
        """Get query, retrieved context, prompts, cfg"""
        return shared["query"], shared['prompts'], shared['cfg']

    def exec(self, inputs):
        """Classify document to retrieve"""
        query, prompts, cfg = inputs
        system_prompt = prompts['system']['document_classification']
        user_prompt = prompts['user']['document_classification']
        model_params = cfg['llm']
        system_format_args = {'main_user':cfg['user_info']['main_user']}
        user_format_args = {'user_question':query}
        answer = llm.query_llm(system_prompt,user_prompt,system_format_args,user_format_args,model_params)
        answer = parsing.extract_xml(answer, 'document')
        return answer

    def post(self, shared, prep_res, exec_res):
        """Store generated answer in shared store"""
        shared["read_document"] = exec_res
        logger.info(f"[DocumentClassification] {exec_res}")
        return "default"

class RetrieveContext(Node):
    def prep(self, shared):
        """Get query, retriever, and cfg from shared store"""
        return shared["query"], shared["retriever"], shared["cfg"]

    def exec(self, inputs):
        """perform retrieval with bm25 and cosine similarity, rerank, reconstruct context"""
        query, retriever, cfg = inputs
        results_s = retriever.sparse_retrieval(query, cfg['retrieval']['top_k_sparse'])
        results_d, q_emb = retriever.dense_retrieval(query, cfg['retrieval']['top_k_dense'])
        results = np.unique(np.hstack([results_d, results_s])).reshape(1, -1)
        reranked_results = retriever.rerank(q_emb, results, cfg['retrieval']['top_k_reranked'])
        docs, out = retriever.reconstruct_docs(reranked_results)

        return {"documents": docs,"context": out}

    def post(self, shared, prep_res, exec_res):
        """Store retrieved documents in shared store"""
        shared["retrieved_context"] = exec_res
        logger.info(f"[RetrieveContext] retrieved {len(exec_res['documents'])} chunks")
        return "default"

class RetrieveDocument(Node):
    def prep(self, shared):
        """Get query, retriever, and document name from shared store"""
        return shared["query"], shared["retriever"], shared['read_document']

    def exec(self, inputs):
        """perform retrieval document name, reconstruct context"""
        query, retriever, read_document = inputs
        chunks=[[v.get('chunk_id') for v in retriever.chunks if v.get('source') == read_document]]
        docs, out = retriever.reconstruct_docs(chunks)

        return {"documents": docs,"context": out}

    def post(self, shared, prep_res, exec_res):
        """Store retrieved documents in shared store"""
        shared["retrieved_context"] = exec_res
        logger.info(f"[RetrieveDocument] read {shared['read_document']}")
        return "default"

class AnswerQuestion(Node):
    def prep(self, shared):
        """Get query, retrieved context, prompts, cfg"""
        return shared["query"], shared["retrieved_context"], shared['prompts'], shared['cfg']

    def exec(self, inputs):
        """Generate an answer using the LLM"""
        query, retrieved_context, prompts, cfg = inputs
        system_prompt = prompts['system']['answer']
        user_prompt = prompts['user']['answer']
        model_params = cfg['llm']
        system_format_args = {'main_user':cfg['user_info']['main_user'],'linkedin_url':cfg['user_info']['linkedin'],
                              'email_address':cfg['user_info']['email']}
        user_format_args = {'user_question':query,'retrieved_context':retrieved_context['context']}
        answer = llm.query_llm(system_prompt,user_prompt,system_format_args,user_format_args,model_params)
        return answer

    def post(self, shared, prep_res, exec_res):
        """Store generated answer in shared store"""
        hl = shared['cfg']['history_length']
        history = shared.get('history', [])
        history.append({'generated_answer': exec_res})
        shared['history'] = history[-hl:]
        shared["generated_answer"] = exec_res
        logger.info(f"[AnswerQuestion] done")
        return "default"

class GenericAnswer(Node):
    def prep(self, shared):
        """Get query, prompts, cfg"""
        return shared["query"], shared['prompts'], shared['cfg']

    def exec(self, inputs):
        """Generate an answer using the LLM"""
        query, prompts, cfg = inputs
        char_limit = cfg['query_char_limit']
        if query != f'too many characters in the query - keep the question within {char_limit} characters':
            system_prompt = prompts['system']['generic_answer']
            user_prompt = prompts['user']['generic_answer']
            model_params = cfg['llm']
            system_format_args = {'main_user':cfg['user_info']['main_user'],'linkedin_url':cfg['user_info']['linkedin'],
                                  'email_address':cfg['user_info']['email']}
            user_format_args = {'user_question':query}
            answer = llm.query_llm(system_prompt,user_prompt,system_format_args,user_format_args,model_params)
        else:
            answer = query
        return answer

    def post(self, shared, prep_res, exec_res):
        """Store generated answer in shared store"""
        hl = shared['cfg']['history_length']
        history = shared.get('history', [])
        history.append({'generated_answer': exec_res})
        shared['history'] = history[-hl:]
        shared["generated_answer"] = exec_res
        logger.info(f"[GenericAnswer] done")
        return "default"

class NoAnswerQuestion(Node):
    def prep(self, shared):
        """Return precooked response for out-of-scope questions"""
        return shared['prompts']

    def exec(self, inputs):
        """pick random answer"""
        system_prompt = inputs['system']['no_answer']
        answer = random.choice(system_prompt)
        return answer

    def post(self, shared, prep_res, exec_res):
        """Store generated answer in shared store"""
        hl = shared['cfg']['history_length']
        history = shared.get('history', [])
        history.append({'generated_answer': exec_res})
        shared['history'] = history[-hl:]
        shared["generated_answer"] = exec_res
        logger.info(f"[NoAnswerQuestion] done")
        return "default"