import os, re, time, json, hashlib, threading
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")

JD_APP_KEY = os.getenv("JD_APP_KEY")
JD_APP_SECRET = os.getenv("JD_APP_SECRET")
JD_SITE_ID = os.getenv("JD_SITE_ID")
JD_POSITION_ID = int(os.getenv("JD_POSITION_ID", "0"))

_token_cache = {"token": None, "expire_at": 0}
_lock = threading.Lock()

def get_tenant_access_token():
    with _lock:
        now = time.time()
        if _token_cache["token"] and now < _token_cache["expire_at"]:
            return _token_cache["token"]
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        r = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=8)
        r.raise_for_status()
        data = r.json()
        if data.get("code") == 0:
            _token_cache["token"] = data["tenant_access_token"]
            _token_cache["expire_at"] = now + data.get("expire", 7000) - 60
            return _token_cache["token"]
        raise RuntimeError(f"get_tenant_access_token failed: {data}")

def jd_sign(app_key, app_secret, method, param_json, access_token=None):
    params = {
        "app_key": app_key,
        "method": method,
        "v": "1.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sign_method": "md5",
        "360buy_param_json": param_json
    }
    if access_token:
        params["access_token"] = access_token
    s = app_secret + "".join(f"{k}{params[k]}" for k in sorted(params)) + app_secret
    params["sign"] = hashlib.md5(s.encode("utf-8")).hexdigest().upper()
    return params

def jd_convert(material_url, site_id, position_id, sub_union_id, app_key, app_secret):
    body = {
        "promotionCodeReq": {
            "materialId": material_url,
            "siteId": str(site_id),
            "positionId": position_id,
            "subUnionId": (sub_union_id or "unknown")[:80]
        }
    }
    param_json = json.dumps(body, ensure_ascii=False, separators=(',', ':'))
    params = jd_sign(app_key, app_secret, "jd.union.open.promotion.common.get", param_json)
    r = requests.post("https://api.jd.com/routerjson", data=params, timeout=8)
    r.raise_for_status()
    p = r.json()
    result = json.loads(p["jd_union_open_promotion_common_get_response"]["result"])
    data = result.get("data") or {}
    return data.get("shortURL") or data.get("shortUrl") or data.get("clickURL")

JD_URL_RE = re.compile(
    r'(https?://[^\s<>"\)]*?(?:jd\.com|jd\.hk|jingxi\.com|m\.jd\.com|u\.jd\.com)[^\s<>"\)]*)',
    re.I,
)

def extract_text_from_message_content(content_json: str) -> str:
    try:
        obj = json.loads(content_json)
        return obj.get("text", "")
    except Exception:
        return ""

def feishu_reply_message(message_id: str, text: str):
    token = get_tenant_access_token()
    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
    body = {"msg_type": "text", "content": json.dumps({"text": text}, ensure_ascii=False)}
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(url, headers=headers, json=body, timeout=8)
    return r.status_code

@app.route("/event", methods=["POST"])
def event():
    data = request.get_json(silent=True) or {}
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge", "")})

    header = data.get("header", {})
    event_type = header.get("event_type")
    if event_type != "im.message.receive_v1":
        return jsonify({"code": 0})

    event = data.get("event", {})
    msg = event.get("message", {})
    msg_id = msg.get("message_id")
    if event.get("sender", {}).get("sender_type") == "bot":
        return jsonify({"code": 0})

    text = extract_text_from_message_content(msg.get("content", "{}"))
    m = JD_URL_RE.search(text)
    if not m:
        return jsonify({"code": 0})

    jd_url = m.group(1)
    open_id = event.get("sender", {}).get("sender_id", {}).get("open_id", "unknown")
    try:
        short_url = jd_convert(
            material_url=jd_url,
            site_id=JD_SITE_ID,
            position_id=JD_POSITION_ID,
            sub_union_id=open_id,
            app_key=JD_APP_KEY,
            app_secret=JD_APP_SECRET,
        )
        if short_url:
            feishu_reply_message(msg_id, f"✅ 返现链接：{short_url}")
        else:
            feishu_reply_message(msg_id, "❌ 转链失败，请换个商品链接再试。")
    except Exception as e:
        feishu_reply_message(msg_id, f"❌ 转链异常：{e}")
    return jsonify({"code": 0})

@app.get("/healthz")
def healthz():
    return "ok", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
