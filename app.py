import os
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


@app.route('/v1/<path:path>', methods=['POST', 'GET', 'OPTIONS'])
def openai_proxy(path):
    api = f"/v1/{path}"
    url = "https://api.openai.com" + api

    logger.debug(
        f"api: {api}, method: {request.method}, req: {request.data.decode('utf-8')}, header: {request.headers}")

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
