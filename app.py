import os
import requests
from flask import Flask, request, jsonify, Response
from loguru import logger

if not os.path.exists("config.py"):
    raise Exception('配置文件不存在，请根据config-template.py模板创建config.py文件')
from config import PROXY_KEY, PROXY_IP_PORT, OPENAI_API_KEY

app = Flask(__name__)
proxies = {
    'http': f'http://{PROXY_IP_PORT}',
    'https': f'http://{PROXY_IP_PORT}',
}
url = "https://api.openai.com/v1/chat/completions"


@app.errorhandler(404)
def not_found(error):
    logger.debug(f"req: {request.method} {request.data}")
    return jsonify({'error': 'Not found'}), 404


@app.route('/v1/models', methods=['GET'])
def models():
    rst = {
        "object": "list",
        "data": [
            {
                "id": "gpt-3.5-turbo-0301",
                "object": "model",
                "created": 1677649963,
                "owned_by": "openai",
                "permission": [
                    {
                        "id": "modelperm-vrvwsIOWpZCbya4ceX3Kj4qw",
                        "object": "model_permission",
                        "created": 1679602087,
                        "allow_create_engine": False,
                        "allow_sampling": True,
                        "allow_logprobs": True,
                        "allow_search_indices": False,
                        "allow_view": True,
                        "allow_fine_tuning": False,
                        "organization": "*",
                        "group": None,
                        "is_blocking": False
                    }
                ],
                "root": "gpt-3.5-turbo-0301",
                "parent": None
            },
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": 1677610602,
                "owned_by": "openai",
                "permission": [
                    {
                        "id": "modelperm-M56FXnG1AsIr3SXq8BYPvXJA",
                        "object": "model_permission",
                        "created": 1679602088,
                        "allow_create_engine": False,
                        "allow_sampling": True,
                        "allow_logprobs": True,
                        "allow_search_indices": False,
                        "allow_view": True,
                        "allow_fine_tuning": False,
                        "organization": "*",
                        "group": None,
                        "is_blocking": False
                    }
                ],
                "root": "gpt-3.5-turbo",
                "parent": None
            }
        ]
    }
    return jsonify(rst)


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


@app.route('/v1/chat/completions', methods=['POST', 'OPTIONS'])
def openai_proxy():
    logger.debug(f"method: {request.method}, req: {request.data.decode('utf-8')}, header: {request.headers}")

    if request.method == 'OPTIONS':
        resp = requests.options(url, headers=get_req_headers(request), proxies=proxies)
        return Response(resp.content, resp.status_code, get_resp_headers(resp),
                        mimetype=resp.headers.get('Content-Type'))

    if request.headers.get("Authorization") != "Bearer " + PROXY_KEY:
        msg = f"Invalid API key: {request.headers.get('Authorization')}"
        logger.warning(msg)
        return jsonify({"error": msg}), 401

    if "application/json" not in request.headers.get("Content-Type"):
        msg = f"Invalid Content-Type: {request.headers.get('Content-Type')}"
        logger.warning(msg)
        return jsonify({"error": msg}), 401

    if request.json.get('model') not in ['gpt-3.5-turbo-0301', "gpt-3.5-turbo"]:
        msg = f"Invalid model: {request.json.get('model')}"
        logger.warning(msg)
        return jsonify({"error": msg}), 401

    r_json = request.json

    headers = get_req_headers(request)
    headers['Authorization'] = "Bearer " + OPENAI_API_KEY

    if PROXY_IP_PORT:

        resp = requests.post(url=url, headers=headers, json=r_json, proxies=proxies, stream=True)
    else:
        resp = requests.post(url=url, headers=headers, json=r_json, stream=True)
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
