import asyncio
import os
from dataclasses import asdict
from typing import List, Union, Optional
from dotenv import load_dotenv
import random
import async_timeout
from openai import OpenAI, AsyncOpenAI
from tenacity import retry, wait_random_exponential, stop_after_attempt
import time
from typing import Dict, Any

from swarm.utils.log import logger
from swarm.llm.format import Message
from swarm.llm.price import cost_count
from swarm.llm.llm import LLM
from swarm.llm.llm_registry import LLMRegistry


def get_url_and_keys():
    api_url = os.environ.get("GPTSWARM_API_URL", "https://api.vsegpt.ru/v1")
    if "openai" in api_url:
        api_keys = [os.environ.get("OPENAI_API_KEY")]
    else:
        api_keys = [os.environ.get("OPENAI_API_KEY")]
    return api_url, api_keys

LLM_URL, OPENAI_API_KEYS = get_url_and_keys()

LM_STUDIO_URL = LLM_URL
#
# LLM_URL = "https://api.vsegpt.ru/v1"
#
# load_dotenv()
# OPENAI_API_KEYS=[os.getenv(f"VSE_GPT_API_KEY")]
# for i in range(10):
#     if os.getenv(f"OPENAI_API_KEY{i}"):
#         OPENAI_API_KEYS.append(os.getenv(f"OPENAI_API_KEY{i}"))


def gpt_chat(
    model: str,
    messages: List[Message],
    max_tokens: int = 8192,
    temperature: float = 0.0,
    num_comps=1,
    return_cost=False,
) -> Union[List[str], str]:
    if messages[0].content == '$skip$':
        return ''

    api_kwargs: Dict[str, Any]
    api_kwargs = dict(base_url=LLM_URL, api_key=random.sample(OPENAI_API_KEYS, 1)[0])
    # api_key = random.sample(OPENAI_API_KEYS, 1)[0]
    # api_kwargs = dict(api_key=api_key)
    client = OpenAI(**api_kwargs)

    formated_messages = [asdict(message) for message in messages]
    response = client.chat.completions.create(model=model,
    messages=formated_messages,
    max_tokens=max_tokens,
    temperature=temperature,
    top_p=1,
    frequency_penalty=0.0,
    presence_penalty=0.0,
    n=num_comps)
    
    if num_comps == 1:
        # cost_count(response, model)
        return response.choices[0].message.content

    # cost_count(response, model)

    return [choice.message.content for choice in response.choices]


@retry(wait=wait_random_exponential(max=100), stop=stop_after_attempt(10))
async def gpt_achat(
    model: str,
    messages: List[Message],
    max_tokens: int = 8192,
    temperature: float = 0.0,
    num_comps=1,
    return_cost=False,
) -> Union[List[str], str]:
    if messages[0].content == '$skip$':
        return '' 

    api_kwargs: Dict[str, Any]
    api_kwargs = dict(base_url=LLM_URL, api_key=random.sample(OPENAI_API_KEYS, 1)[0])
    aclient = AsyncOpenAI(**api_kwargs)

    formated_messages = [asdict(message) for message in messages]
    try:
        async with async_timeout.timeout(1000):
            response = await aclient.chat.completions.create(model=model,
            messages=formated_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=1,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            n=num_comps)
    except asyncio.TimeoutError:
        print('Timeout')
        raise TimeoutError("GPT Timeout")
    if num_comps == 1:
        # cost_count(response, model)
        return response.choices[0].message.content

    # cost_count(response, model)
    return [choice.message.content for choice in response.choices]


@LLMRegistry.register('GPTChat')
class GPTChat(LLM):

    def __init__(self, model_name: str):
        self.model_name = model_name

    async def agen(
        self,
        messages: List[Message],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        num_comps: Optional[int] = None,
        ) -> Union[List[str], str]:

        if max_tokens is None:
            max_tokens = self.DEFAULT_MAX_TOKENS
        if temperature is None:
            temperature = self.DEFAULT_TEMPERATURE
        if num_comps is None:
            num_comps = self.DEFUALT_NUM_COMPLETIONS

        if isinstance(messages, str):
            messages = [Message(role="user", content=messages)]

        return await gpt_achat(self.model_name,
                               messages,
                               max_tokens,
                               temperature,
                               num_comps)

    def gen(
        self,
        messages: List[Message],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        num_comps: Optional[int] = None,
        ) -> Union[List[str], str]:

        if max_tokens is None:
            max_tokens = self.DEFAULT_MAX_TOKENS
        if temperature is None:
            temperature = self.DEFAULT_TEMPERATURE
        if num_comps is None:
            num_comps = self.DEFUALT_NUM_COMPLETIONS

        if isinstance(messages, str):
            messages = [Message(role="user", content=messages)]

        return gpt_chat(self.model_name,
                        messages, 
                        max_tokens,
                        temperature,
                        num_comps)
