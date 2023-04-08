# openai_proxy_flask
A reverse proxy program for an OpenAI API implemented in Flask, which is straightforward.一个简单的flask实现的openai api的反向代理程序

# 配置文件示例
```python
# 认证被代理端
PROXY_KEY = "sk-abc123456789abc123456789abc123456789abc123456789"

# openai API 密钥
OPENAI_API_KEY = 'sk-ThisIsRealOpenAiApiKey11111111111111111111111111'

# 科学上网，http的代理, 不走代理时设置为空字符串
# PROXY_IP_PORT = ""
PROXY_IP_PORT = "127.0.0.1:7890"

# 主机
HOST = "0.0.0.0"

# 监听端口Port，https时当前目录需要有ssl.cert和ssl.key文件
PORT_HTTP = 52081
PORT_HTTPS = 52444

```

# 运行
```bash
    python3 run_openai_api_http.py
```
或者
```bash
    python3 run_openai_api_https.py
```