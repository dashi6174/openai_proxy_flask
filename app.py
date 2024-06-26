import json
import os
from urllib.parse import urlparse

import openai
import requests
from flask import Flask, request, jsonify, Response
from loguru import logger

if not os.path.exists("config.py"):
    raise Exception('配置文件不存在，请根据config-template.py模板创建config.py文件')
from config import *

app = Flask(__name__)

api_list = [
    "/v1/chat/completions",
    "/v1/embeddings"
]


@app.errorhandler(404)
def not_found(error):
    logger.debug(f"req: {request.method} {request.data}")
    return jsonify({'error': 'Not found'}), 404


def get_req_headers(request):
    headers = {}
    for k, v in request.headers:
        if k not in ['Host', 'Accept-Encoding', 'Content-Length', 'Transfer-Encoding', 'Connection']:
            headers[k] = v
    return headers


def get_resp_headers(resp):
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in resp.headers.items() if name.lower() not in excluded_headers]
    return headers


def cre_img(api, r_json, host_url, proxies):
    # 检查
    if not api == "/v1/chat/completions":
        return None

    if r_json['messages'][-1]['role'] == 'user' and r_json['messages'][-1]['content'][:3] == '【画】':
        prompt = r_json['messages'][-1]['content'][3:]
    elif len(r_json['messages']) > 1 and r_json['messages'][-1]['role'] == 'system' \
            and r_json['messages'][-2]['role'] == 'user' and r_json['messages'][-2]['content'][:3] == '【画】':
        # system role在最后一条
        prompt = r_json['messages'][-2]['content'][3:]
    else:
        return None

    # 图片大小
    size_map = {"【s】": '256x256', "【m】": '512x512', "【b】": '1024x1024'}
    if prompt[:3] in size_map:
        size = size_map[prompt[:3]]
        prompt = prompt[3:]
    else:
        size = '512x512'

    # 图片数量
    n_map = {"【1】": 1, "【2】": 2, "【3】": 3, "【4】": 4, "【5】": 5,
             "【6】": 6, "【7】": 7, "【8】": 8, "【9】": 9, "【10】": 10}
    if prompt[:3] in n_map:
        n = n_map[prompt[:3]]
        prompt = prompt[3:]
    elif prompt[:4] in n_map:
        n = n_map[prompt[:4]]
        prompt = prompt[4:]
    else:
        n = 1

    # 请求
    logger.info(f"[OPEN_AI] image_query={prompt}")
    if proxies:
        openai.proxy = proxies
    response = openai.Image.create(
        api_key=OPENAI_API_KEY,
        prompt=prompt,
        n=n,
        size=size,
    )

    # 组装
    image_url_arr = []
    for item in response['data']:
        logger.info(f"[OPEN_AI] image_url={item['url']}")

        filename = f"static/imgs/{os.path.basename(urlparse(item['url']).path)}"
        if proxies:
            response = requests.get(item['url'], proxies=proxies)
        else:
            response = requests.get(item['url'])
        with open(filename, 'wb') as f:
            f.write(response.content)
        image_url_arr.append(f"![image]({host_url + filename})")

    # 响应
    if r_json.get('stream'):
        imgs = '  \\n'.join(image_url_arr)
        body = 'data: {"id":"chatcmpl-7KlAnQk1IUTMEkRgAztMDkjCMM1Sy","object":"chat.completion.chunk",' \
               '"created":1685450197,"model":"gpt-3.5-turbo-0301","choices":[{"delta":{"content":"' \
               + f"{imgs}" + '"},"index":0,"finish_reason":null}]}\n\n' \
               + 'data: {"id":"chatcmpl-7KlAnQk1IUTMEkRgAztMDkjCMM1Sy","object":"chat.completion.chunk",' \
                 '"created":1685450197,"model":"gpt-3.5-turbo-0301","choices":[{"delta":{},' \
                 '"index":0,"finish_reason":stop}]}\n\n' \
               + 'data: [DONE]\n\n'
        logger.debug(body)
        return Response(body, 200, headers={}, mimetype="text/event-stream")

    else:
        imgs = '  \n'.join(image_url_arr)
        body = {"id": "chatcmpl-7KlAnQk1IUTMEkRgAztMDkjCMM1Sy", "object": "chat.completion", "created": 1685450197,
                "model": "gpt-3.5-turbo-0301",
                "usage": {"prompt_tokens": len(prompt), "completion_tokens": len(imgs),
                          "total_tokens": len(prompt) + len(imgs)},
                "choices": [{"message": {"role": "assistant", "content": imgs}, "finish_reason": "stop", "index": 0}]}
        logger.debug(body)
        return Response(json.dumps(body), 200, headers={}, mimetype="application/json")


@app.route('/v1/<path:path>', methods=['POST', 'GET', 'OPTIONS'])
def openai_proxy(path):
    api = f"/v1/{path}"
    url = f"{OPENAI_BASE_URL}/{path}"

    logger.debug(
        f"api: {api}, method: {request.method}, header: {request.headers}")

    # 代理
    if PROXY_IP_PORT:
        proxies = {
            'http': f'http://{PROXY_IP_PORT}',
            'https': f'http://{PROXY_IP_PORT}',
        }
    else:
        proxies = None

    # options不用带key
    if request.method == 'OPTIONS':
        resp = requests.options(url, headers=get_req_headers(request), proxies=proxies)
        return Response(resp.content, resp.status_code, get_resp_headers(resp),
                        mimetype=resp.headers.get('Content-Type'))

    # 校验key

    if request.headers.get("Authorization") != "Bearer " + PROXY_KEY:
        msg = f"Invalid API key: {request.headers.get('Authorization')}"
        logger.warning(msg)
        return jsonify({"error": msg}), 401

    # todo: 校验api是否已支持，哪些耗钱的api要剔除掉，DALL·E 、 Davinci 等

    # todo: 校验个人gpt4.0额度

    # 请求参数
    if request.method == "GET":
        r_json = None
    else:
        r_json = request.json
        logger.debug("Request body: {}".format(r_json))
        # 通过特殊的前缀支持画图输出
        resp = cre_img(api, r_json, request.host_url, proxies)
        if resp:
            return resp

    headers = get_req_headers(request)
    headers['Authorization'] = "Bearer " + OPENAI_API_KEY

    # 向openai请求
    if request.method == "GET":
        resp = requests.get(url=url, headers=headers, proxies=proxies, stream=True)
    else:
        resp = requests.post(url=url, headers=headers, json=r_json, proxies=proxies, stream=True)
    logger.info(f"resp.headers: {resp.headers}")
    headers = get_resp_headers(resp)

    def generate():
        msgs = b''
        for item in resp:
            msgs += item
            yield item
        else:
            logger.info(f"rsp: {msgs.decode('utf-8')}")

    return Response(generate(), resp.status_code, headers, mimetype=resp.raw.headers.get('Content-Type'))
