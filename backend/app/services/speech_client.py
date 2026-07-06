"""Speech services: edge-tts (TTS) + Alibaba ASR (placeholder)."""
import asyncio
import base64
import io
import tempfile
import os


async def speech_to_text(audio_bytes: bytes, audio_format: str = "mp3") -> tuple[str, float]:
    """ASR - currently mock. Returns (text, confidence)."""
    size = len(audio_bytes)
    if size < 200:
        return ("", 0.0)
    # TODO: connect real ASR (Alibaba / Whisper / etc.)
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
