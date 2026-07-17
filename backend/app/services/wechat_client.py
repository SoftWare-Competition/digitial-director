"""WeChat Mini Program API client — 真实的 code → openid 交换 & 手机号解密."""

import time
import httpx
from app.config import settings

WECHAT_API = "https://api.weixin.qq.com/sns/jscode2session"
WECHAT_TOKEN_API = "https://api.weixin.qq.com/cgi-bin/token"
WECHAT_PHONE_API = "https://api.weixin.qq.com/wxa/business/getuserphonenumber"

# 内存缓存 access_token（生产环境建议用 Redis）
_cached_token: str = ""
_cached_token_expires: float = 0.0


def _is_configured() -> bool:
    return bool(settings.wechat_appid and settings.wechat_appid != "your_wechat_appid")


async def _get_access_token() -> str | None:
    """获取/刷新微信公众号 access_token（带缓存，有效期 2 小时）"""
    global _cached_token, _cached_token_expires

    if not _is_configured():
        print("[WeChat] WECHAT_APPID 未配置，无法获取 access_token")
        return None

    # 缓存未过期直接返回
    if _cached_token and time.time() < _cached_token_expires - 60:
        return _cached_token

    params = {
        "grant_type": "client_credential",
        "appid": settings.wechat_appid,
        "secret": settings.wechat_secret,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(WECHAT_TOKEN_API, params=params)
            data = resp.json()

        if "access_token" in data:
            _cached_token = data["access_token"]
            _cached_token_expires = time.time() + data.get("expires_in", 7200)
            print(f"[WeChat] access_token 刷新成功，有效期 {data.get('expires_in')}s")
            return _cached_token
        else:
            print(f"[WeChat] access_token 获取失败: {data}")
            return None
    except Exception as e:
        print(f"[WeChat] access_token 请求异常: {e}")
        return None


async def wechat_code_to_session(js_code: str) -> dict | None:
    """
    调用微信官方 API，用临时 code 换取 openid + session_key。

    返回: {"openid": "...", "session_key": "...", "unionid": "..."?}
    失败: 返回 None
    """
    if not _is_configured():
        print("[WeChat] WECHAT_APPID 未配置，跳过真实登录")
        return None

    params = {
        "appid": settings.wechat_appid,
        "secret": settings.wechat_secret,
        "js_code": js_code,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(WECHAT_API, params=params)
            data = resp.json()

        if "errcode" in data and data["errcode"] != 0:
            print(f"[WeChat] jscode2session 错误: errcode={data.get('errcode')} errmsg={data.get('errmsg')}")
            return None

        print(f"[WeChat] jscode2session 成功, openid={data.get('openid', '')[:8]}***")
        return {
            "openid": data.get("openid", ""),
            "session_key": data.get("session_key", ""),
            "unionid": data.get("unionid", ""),
        }
    except Exception as e:
        print(f"[WeChat] jscode2session 请求失败: {e}")
        return None


async def exchange_phone_number(phone_code: str) -> str | None:
    """
    用 getPhoneNumber 返回的动态 code 换取真实手机号。

    前端流程: <button open-type="getPhoneNumber"> → e.detail.code
    后端用 access_token + code 调微信接口获取手机号。

    返回: 手机号字符串（如 "138xxxx1234"），失败返回 None
    """
    if not _is_configured():
        print("[WeChat] 未配置，无法获取手机号")
        return None

    access_token = await _get_access_token()
    if not access_token:
        return None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{WECHAT_PHONE_API}?access_token={access_token}",
                json={"code": phone_code},
            )
            data = resp.json()

        if data.get("errcode") == 0:
            phone_info = data.get("phone_info", {})
            phone = phone_info.get("purePhoneNumber") or phone_info.get("phoneNumber", "")
            print(f"[WeChat] 手机号获取成功: {phone[:3]}****{phone[-4:]}")
            return phone
        else:
            print(f"[WeChat] 手机号获取失败: errcode={data.get('errcode')} errmsg={data.get('errmsg')}")
            return None
    except Exception as e:
        print(f"[WeChat] 手机号请求异常: {e}")
        return None
