import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache


logger = logging.getLogger(__name__)
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


class WeChatDeliveryError(Exception):
    pass


class WeChatSender:
    """微信通知发送器：本地日志、通用 Webhook、公众号模板消息。"""

    token_cache_key = "wechat:official-account:access-token"

    def __init__(self):
        self.mode = settings.WECHAT_PUSH_MODE

    @property
    def is_official_account_ready(self):
        return bool(
            settings.WECHAT_OFFICIAL_ACCOUNT_APP_ID
            and settings.WECHAT_OFFICIAL_ACCOUNT_APP_SECRET
            and settings.WECHAT_TEMPLATE_ID
        )

    def send(self, *, openid, title, message, scheduled_at=None):
        if not openid:
            raise WeChatDeliveryError("学生尚未绑定微信。")
        if self.mode == "log":
            logger.info("微信推送模拟消息 openid=%s title=%s message=%s", openid, title, message)
            return
        if self.mode == "webhook":
            return self._send_webhook(openid=openid, title=title, message=message)
        if self.mode == "official_account":
            return self._send_official_account(
                openid=openid,
                title=title,
                message=message,
                scheduled_at=scheduled_at,
            )
        raise WeChatDeliveryError(f"不支持的微信推送模式：{self.mode}")

    def oauth_url(self, *, redirect_uri, state):
        if self.mode != "official_account" or not self.is_official_account_ready:
            raise WeChatDeliveryError("微信公众号通道尚未完成配置。")
        query = urlencode(
            {
                "appid": settings.WECHAT_OFFICIAL_ACCOUNT_APP_ID,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "snsapi_base",
                "state": state,
            }
        )
        return f"https://open.weixin.qq.com/connect/oauth2/authorize?{query}#wechat_redirect"

    def exchange_oauth_code(self, code):
        if not self.is_official_account_ready:
            raise WeChatDeliveryError("微信公众号通道尚未完成配置。")
        query = urlencode(
            {
                "appid": settings.WECHAT_OFFICIAL_ACCOUNT_APP_ID,
                "secret": settings.WECHAT_OFFICIAL_ACCOUNT_APP_SECRET,
                "code": code,
                "grant_type": "authorization_code",
            }
        )
        payload = self._request_json(f"https://api.weixin.qq.com/sns/oauth2/access_token?{query}")
        openid = payload.get("openid")
        if not openid:
            raise WeChatDeliveryError(self._wechat_error(payload, "微信授权未返回用户标识。"))
        return openid

    def _send_webhook(self, *, openid, title, message):
        endpoint = settings.WECHAT_PUSH_ENDPOINT
        if not endpoint:
            raise WeChatDeliveryError("未配置 WECHAT_PUSH_ENDPOINT。")
        self._request_json(
            endpoint,
            data={"openid": openid, "title": title, "message": message},
        )

    def _send_official_account(self, *, openid, title, message, scheduled_at):
        if not self.is_official_account_ready:
            raise WeChatDeliveryError("微信公众号模板消息配置不完整。")
        token = self._access_token()
        payload = {
            "touser": openid,
            "template_id": settings.WECHAT_TEMPLATE_ID,
            "data": self._template_data(
                title=title,
                message=message,
                scheduled_at=scheduled_at,
            ),
        }
        if settings.WECHAT_TEMPLATE_URL:
            payload["url"] = settings.WECHAT_TEMPLATE_URL
        response = self._request_json(
            f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}",
            data=payload,
        )
        if response.get("errcode", 0) != 0:
            raise WeChatDeliveryError(self._wechat_error(response, "微信模板消息发送失败。"))

    def _access_token(self):
        token = cache.get(self.token_cache_key)
        if token:
            return token
        query = urlencode(
            {
                "grant_type": "client_credential",
                "appid": settings.WECHAT_OFFICIAL_ACCOUNT_APP_ID,
                "secret": settings.WECHAT_OFFICIAL_ACCOUNT_APP_SECRET,
            }
        )
        response = self._request_json(f"https://api.weixin.qq.com/cgi-bin/token?{query}")
        token = response.get("access_token")
        if not token:
            raise WeChatDeliveryError(self._wechat_error(response, "无法获取微信公众号访问令牌。"))
        expires_in = max(int(response.get("expires_in", 7200)) - 300, 60)
        cache.set(self.token_cache_key, token, expires_in)
        return token

    def _template_data(self, *, title, message, scheduled_at):
        scheduled = (
            scheduled_at.astimezone(SHANGHAI_TZ).strftime("%Y-%m-%d %H:%M")
            if scheduled_at
            else ""
        )
        values = {
            "title": title,
            "message": message,
            "scheduled_at": scheduled,
        }
        template = settings.WECHAT_TEMPLATE_DATA
        if not isinstance(template, dict) or not template:
            raise WeChatDeliveryError("WECHAT_TEMPLATE_DATA 必须是非空 JSON 对象。")
        try:
            return {
                key: {"value": str(value).format_map(values)}
                for key, value in template.items()
            }
        except KeyError as exc:
            raise WeChatDeliveryError(
                f"WECHAT_TEMPLATE_DATA 使用了未知变量：{exc.args[0]}。"
            ) from exc

    def _request_json(self, url, *, data=None):
        request = Request(
            url,
            data=json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None,
            headers={"Content-Type": "application/json"} if data is not None else {},
            method="POST" if data is not None else "GET",
        )
        try:
            with urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise WeChatDeliveryError(f"微信通道返回 HTTP {exc.code}。") from exc
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise WeChatDeliveryError(f"微信通道连接失败：{exc}") from exc

    @staticmethod
    def _wechat_error(payload, fallback):
        code = payload.get("errcode")
        message = payload.get("errmsg")
        return f"{fallback} ({code}: {message})" if code is not None else fallback
