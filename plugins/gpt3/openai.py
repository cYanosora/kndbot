import httpx
from typing import Any, Tuple
from .config import config


def remove_punctuation(text: str) -> str:
    """ 去除句首的多余标点符号 """
    import string
    for i in range(len(text)):
        if text[i] not in string.punctuation:
            return text[i:]
    return ""


async def request_api(proxy: str, key: str, preset: str, conversation: list, msg: str) -> Tuple[Any, bool]:
    """
    获取openai gpt3 api 回复
    :param proxy: 代理
    :param key: 密钥
    :param preset: 人格
    :param conversation: 历史会话
    :param msg: 消息内容
    :return:
    """
    if proxy:
        proxies = {
            "http://": proxy,
            "https://": proxy,
        }
    else:
        proxies = {}

    system = [
        {"role": "system", "content": preset}
    ]
    prompt = {"role": "user", "content": msg}
    conversation.append(prompt)
    client = httpx.AsyncClient(proxies=proxies, timeout=None)
    try:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": config.gpt3_model,
                "messages": system + conversation,
                "max_tokens": config.gpt3_max_tokens,
            },
        )
        response = response.json()
        res: str = remove_punctuation(response['choices'][0]['message']['content'].strip())
        conversation.append({"role": "assistant", "content": res})
        return response, True
    except httpx.ConnectTimeout as e:
        return f"网络不太好: {e.request.url}", False
    except Exception as e:
        return f"发生未知错误: {type(e)}", False
