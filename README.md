# Feishu JD Converter (Railway)

一个极简的飞书机器人：群里有人发 JD 链接 -> 机器人回复你的返现短链。可一键部署到 Railway。

## 本地运行
```bash
python -m venv .venv && . .venv/bin/activate  # Windows 用 .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # 然后填好变量
python main.py
# 本地测试健康检查
curl http://127.0.0.1:8080/healthz
```

## Railway 部署（Docker）
1. 新建一个 Github 仓库，上传本项目（包含 Dockerfile）。
2. 打开 Railway -> New Project -> Deploy from GitHub，选这个仓库。
3. 在 Railway 的 **Variables** 中添加：
   - FEISHU_APP_ID
   - FEISHU_APP_SECRET
   - JD_APP_KEY
   - JD_APP_SECRET
   - JD_SITE_ID
   - JD_POSITION_ID
4. 部署完成后，复制分配的域名，例如 `https://xxx.up.railway.app`。
5. 在飞书自建应用的 *事件订阅* 中：
   - 请求网址填入 `https://xxx.up.railway.app/event`
   - 订阅事件：`im.message.receive_v1`
   - 打开机器人并安装到目标群
6. 在群里丢一个京东链接，机器人会回复返现短链。

## 常见问题
- 403/无权限：确保机器人已经安装进群，并勾选了“读群消息”“以机器人身份发消息”两项权限。
- URL 验证失败：先访问 `https://xxx.up.railway.app/healthz` 确认服务在线；检查防火墙/地区访问是否受限。
- 转链失败：检查 JD 联盟 `app_key/app_secret`、`siteId`、`positionId` 是否正确，确认推广位与站点类型匹配。
- 对账返现：此项目只做“转链即回链”。要结算返现，再加一个定时任务调用 `order.row.query` 即可。

## 生产建议
- 将每个群配一个 `positionId`，统计更清晰。
- 为安全与稳定，可在飞书回调里验证签名，并增加日志/速率限制。
