"""Speech services: edge-tts (TTS) + Alibaba ASR."""
import asyncio
import base64
import hashlib
import hmac
import io
import json
import os
import subprocess
import tempfile
import time
import uuid
from urllib.parse import quote

import httpx

from app.config import settings


# ---- Alibaba Cloud NLS token ----
def _sign(method: str, params: dict, secret: str) -> str:
    sorted_keys = sorted(params.keys())
    canon = "&".join(f"{quote(k,'')}={quote(str(params[k]),'')}" for k in sorted_keys)
    to_sign = f"{method}&{quote('/','')}&{quote(canon,'')}"
    mac = hmac.new(f"{secret}&".encode(), to_sign.encode(), hashlib.sha1)
    return base64.b64encode(mac.digest()).decode()


def _get_nls_token() -> str:
    ak_id = settings.alibaba_access_key_id
    ak_secret = settings.alibaba_access_key_secret
    if not ak_id or not ak_secret:
        return ""
    params = {
        "AccessKeyId": ak_id, "Action": "CreateToken", "Format": "JSON",
        "RegionId": "cn-shanghai", "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": str(uuid.uuid4()), "SignatureVersion": "1.0",
        "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "Version": "2019-02-28",
    }
    params["Signature"] = _sign("GET", params, ak_secret)
    try:
        resp = httpx.get("https://nls-meta.cn-shanghai.aliyuncs.com/", params=params, timeout=10)
        return resp.json().get("Token", {}).get("Id", "")
    except Exception as e:
        print(f"[NLS] token err: {e}")
        return ""


_token_cache = {"v": "", "exp": 0}

def _cached_token() -> str:
    now = time.time()
    if _token_cache["v"] and now < _token_cache["exp"]:
        return _token_cache["v"]
    t = _get_nls_token()
    if t:
        _token_cache["v"] = t
        _token_cache["exp"] = now + 86000
    return t


def _convert_to_pcm(audio_bytes: bytes) -> bytes:
    """Convert any audio format to PCM 16kHz mono via ffmpeg."""
    try:
        proc = subprocess.run(
            ["ffmpeg", "-i", "pipe:0", "-f", "s16le", "-acodec", "pcm_s16le",
             "-ar", "16000", "-ac", "1", "pipe:1"],
            input=audio_bytes,
            capture_output=True,
            timeout=15,
        )
        if proc.returncode == 0 and len(proc.stdout) > 200:
            return proc.stdout
    except Exception as e:
        print(f"[ASR] ffmpeg err: {e}")
    return b""


async def speech_to_text(audio_bytes: bytes, audio_format: str = "mp3") -> tuple[str, float]:
    """ASR via Alibaba Cloud NLS."""
    if len(audio_bytes) < 200:
        return ("", 0.0)

    appkey = settings.alibaba_asr_appkey
    token = _cached_token()

    if not token or not appkey:
        print("[ASR] No token or appkey configured")
        return ("[语音消息]", 0.85)

    # Convert to PCM if needed
    pcm_bytes = await asyncio.to_thread(_convert_to_pcm, audio_bytes)
    if not pcm_bytes:
        print("[ASR] PCM conversion failed")
        return ("[语音消息]", 0.85)

    # Send to Alibaba NLS
    try:
        url = "https://nls-gateway.cn-shanghai.aliyuncs.com/stream/v1/asr"
        params = {
            "appkey": appkey,
            "format": "pcm",
            "sample_rate": 16000,
            "enable_punctuation_prediction": "true",
            "enable_inverse_text_normalization": "true",
        }
        headers = {"X-NLS-Token": token, "Content-Type": "application/octet-stream"}
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.post(url, params=params, content=pcm_bytes, headers=headers)
            data = resp.json()
            if data.get("status") == 20000000:
                text = data.get("result", "").strip()
                if text:
                    print(f"[ASR] recognized: {text[:60]}")
                    return (text, 0.95)
            print(f"[ASR] NLS status={data.get('status')} msg={data.get('status_text','')}")
    except Exception as e:
        print(f"[ASR] NLS err: {e}")

    return ("[语音消息]", 0.85)


async def text_to_speech(text: str, voice: str = None) -> bytes:
    """TTS using Microsoft Edge TTS (free, neural). Returns MP3 bytes."""
    if not text or not text.strip():
        return b""

    try:
        import edge_tts
        voice_name = voice or "zh-CN-XiaoyiNeural"

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        communicate = edge_tts.Communicate(text, voice_name)
        await communicate.save(tmp_path)

        with open(tmp_path, "rb") as f:
            audio_data = f.read()

        os.unlink(tmp_path)
        return audio_data

    except ImportError:
        return b""  # edge-tts not installed
    except Exception as e:
        print(f"[TTS] Error: {e}")
        return b""


def text_to_speech_base64(text: str, voice: str = None) -> str:
    """Sync wrapper returning base64 encoded MP3."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(_run_async_tts, text, voice)
                return future.result(timeout=30)
        else:
            audio_bytes = loop.run_until_complete(text_to_speech(text, voice))
            if audio_bytes:
                return base64.b64encode(audio_bytes).decode("ascii")
            return ""
    except Exception as e:
        print(f"[TTS sync] Error: {e}")
        return ""


def _run_async_tts(text: str, voice: str = None) -> str:
    """Run async TTS in a separate event loop."""
    loop = asyncio.new_event_loop()
    try:
        audio_bytes = loop.run_until_complete(text_to_speech(text, voice))
        if audio_bytes:
            return base64.b64encode(audio_bytes).decode("ascii")
        return ""
    finally:
        loop.close()
