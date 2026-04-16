import os
from openai import OpenAI

def query_llm(system_prompt: str, user_prompt: str, system_format_args: dict,
              user_format_args: dict, model_params: dict):
    """
    Generalized function to query LLMs with openai.

    Args:
        system_prompt (str): The system prompt.
        user_prompt (str): The user prompt template with placeholders.
        system_format_args (dict): dictionary with arguments to be applied in the system prompt.
        user_format_args (dict): dictionary with arguments to be applied in the user_prompt.
        model_params (dict): model parameters

    Returns:
       str: Response from the LLM.
    """
    # prepare messages
    system_message =  {"role": "system", "content": system_prompt.format(**system_format_args)}
    user_message = {"role": "user", "content": user_prompt.format(**user_format_args)}
    message_payload = {'messages':[system_message,user_message]}
    model_params.update(message_payload)
    # instantiate client
    client = OpenAI(base_url=os.environ['LLM_URL'],api_key=os.environ['LLM_KEY'])
    # build messages payload and call the LLM
    response = client.chat.completions.create(**model_params)
    return response.choices[0].message.content