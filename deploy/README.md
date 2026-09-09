# 生产运行说明

## 本机长期使用（macOS）

本机日常使用只需要访问：

```text
http://127.0.0.1:8000/
```

Vue 前端会在后台启动时自动构建，并由 Django/Daphne 同域提供，不再依赖临时的 Vite 开发服务器。项目附带的 macOS LaunchAgent 会在登录后自动启动服务，意外退出后自动重试：

旧地址 `http://127.0.0.1:5173/` 也会自动跳转到 `8000`，用于兼容浏览器中之前保存的地址。

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ddl.local.plist
launchctl kickstart -k gui/$(id -u)/com.ddl.local
```

查看状态和日志：

```bash
launchctl print gui/$(id -u)/com.ddl.local
tail -f /tmp/ddl-local.log
tail -f /tmp/ddl-local-error.log
```

要停止自启动：

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.ddl.local.plist
```

## 环境变量

复制项目根目录的 `.env.example` 到服务器的 `/etc/ddl/ddl.env`，填写真实域名、Django 密钥、邮箱 SMTP 与微信公众号凭证。不要将该文件提交到版本库。该项目直接读取操作系统环境变量，不会自动加载项目目录中的 `.env` 文件。

生产环境默认不展示学生/教师演示账号。只有在本地演示时才将 `DJANGO_SHOW_DEMO_ACCOUNTS=true`。

`WECHAT_TEMPLATE_DATA` 的键必须与公众号后台选定的模板字段一致。默认字段适用于含 `first`、`keyword1`、`keyword2` 与 `remark` 的模板；如模板字段不同，只修改该 JSON 的键，不需要改代码。

在公众号后台配置网页授权域名，并将回调地址设置为：

```text
https://你的域名/api/wechat/bind/callback/
```

用户在网站设置中点击“绑定微信”后，需要在微信内完成授权。OpenID 只保存在服务器端，不会返回给浏览器。

## 定时提醒

将 `deploy/ddl-notifications.service` 与 `deploy/ddl-notifications.timer` 复制到 `/etc/systemd/system/`，并按实际部署路径调整 `WorkingDirectory`、`ExecStart` 与运行用户。

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ddl-notifications.timer
systemctl list-timers ddl-notifications.timer
```

该任务每分钟运行一次，负责生成站内提醒并发送未投递的微信消息。消息发送成功后会记录时间，重复运行不会重复发送。

部署平台可以使用 `GET /healthz/` 作为健康检查地址；该接口会检查 Django 是否能连接数据库。

## Gunicorn 与 Nginx

将 `deploy/ddl-web.service` 复制到 `/etc/systemd/system/`，将 `deploy/nginx.conf.example` 按域名修改后放入 Nginx 配置目录。`frontend/dist` 是前端构建产物，`/api/`、`/admin/` 和 `/healthz/` 反向代理到 Gunicorn。

```bash
cd /srv/ddl
source .venv/bin/activate
npm --prefix frontend run build
python manage.py migrate
python manage.py collectstatic --noinput
sudo mkdir -p /etc/ddl
sudo chmod 750 /etc/ddl
sudo chmod 640 /etc/ddl/ddl.env
sudo systemctl daemon-reload
sudo systemctl enable --now ddl-web.service
sudo systemctl enable --now ddl-notifications.timer
sudo nginx -t
sudo systemctl reload nginx
```

若使用 `www-data` 运行服务，请保证 `/srv/ddl`、`frontend/dist` 和数据库目录对该用户可读写。

## 上线前检查

```bash
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
python manage.py test
```

当前服务使用 Daphne 运行 ASGI 应用，以支持 WebSocket 聊天：

```bash
daphne -b 127.0.0.1 -p 8000 ddl_project.asgi:application
```

再配合 Nginx 或同类 HTTPS 反向代理，并将 `/ws/` 配置为 WebSocket 代理，同时将前端构建文件与 Django API 部署到同一 HTTPS 域名下。后续多进程部署时，应将频道层切换为 Redis。
