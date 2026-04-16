from backend.inference.nodes import (Contextualize, ScopeDetection, QueryRouter,
                                     DocumentClassification, RetrieveContext, RetrieveDocument,
                                     AnswerQuestion, GenericAnswer,NoAnswerQuestion)
from pocketflow import Flow


def get_rag_flow():
    # Create rag flow for document retrieval and answer generation
    contextualize_node = Contextualize()
    scope_detection_node = ScopeDetection()
    router_node = QueryRouter()
    document_classification_node = DocumentClassification()
    retrieve_context_node = RetrieveContext()
    retrieve_document_node = RetrieveDocument()
    answer_question = AnswerQuestion()
    generic_answer = GenericAnswer()
    no_answer = NoAnswerQuestion()

    # Connect the nodes
    # contextualization
    contextualize_node >> scope_detection_node
    #first routing
    scope_detection_node - "relevant" >> router_node
    scope_detection_node - "generic" >> generic_answer
    scope_detection_node - "out_of_scope" >> no_answer
    #second routing
    router_node - "specific" >> retrieve_context_node
    router_node - "broad" >> document_classification_node >> retrieve_document_node
    #answer
    retrieve_context_node >> answer_question
    retrieve_document_node >> answer_question

    rag_flow = Flow(start=contextualize_node)

    return rag_flow
