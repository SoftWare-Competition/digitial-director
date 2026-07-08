"""
测试完整 Pipeline: 语音输入 → ASR识别 → 文字发送AI → 回复
用法:
    python tests/test_asr_pipeline.py              # 使用模拟文本测试
    python tests/test_asr_pipeline.py audio.wav    # 指定音频文件
    python tests/test_asr_pipeline.py --asr-only audio.wav  # 仅测试ASR
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.speech_client import speech_to_text
from app.services.llm_client import chat as llm_chat
from app.services.speech_client import text_to_speech


async def test_pipeline(audio_path: str = None):
    """端到端测试"""
    print('=' * 60)
    print('  语音识别 -> AI 对话 Pipeline 测试')
    print('=' * 60)

    # Step 1: 加载音频/使用模拟文本
    if audio_path and os.path.exists(audio_path):
        with open(audio_path, 'rb') as f:
            audio_bytes = f.read()
        print(f'\n音频文件: {audio_path} ({len(audio_bytes)} bytes)')
        print('--- Step 1: ASR 语音识别 ---')
        text, confidence = await speech_to_text(audio_bytes)
        if text:
            print(f'  识别成功: "{text}" (置信度: {confidence:.2f})')
        else:
            print('  未识别到语音内容，使用模拟文本')
            text = '灵山大佛有多高？'
    else:
        text = '灵山大佛有多高？'
        print(f'\n使用模拟文本: "{text}"')

    # Step 2: AI 对话
    print('\n--- Step 2: AI 对话 (DeepSeek) ---')
    print(f'  用户: {text}')
    answer = await llm_chat(user_message=text)
    print(f'  小灵: {answer}')

    # Step 3: TTS
    print('\n--- Step 3: TTS 语音合成 (Edge-TTS) ---')
    audio_out = await text_to_speech(answer)
    if audio_out:
        out_path = os.path.join(os.path.dirname(__file__), '..', 'audio', 'test_output.mp3')
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'wb') as f:
            f.write(audio_out)
        print(f'  语音合成完成: test_output.mp3 ({len(audio_out)} bytes)')
    else:
        print('  语音合成失败')

    print('\n' + '=' * 60)
    print('  Pipeline 测试完成!')
    print('=' * 60)


async def test_asr_only(audio_path: str):
    """仅测试 ASR"""
    print('=' * 60)
    print('  ASR 语音识别测试')
    print('=' * 60)
    with open(audio_path, 'rb') as f:
        audio_bytes = f.read()
    print(f'\n音频文件: {audio_path} ({len(audio_bytes)} bytes)')
    text, confidence = await speech_to_text(audio_bytes)
    if text:
        print(f'\n识别结果: "{text}" (置信度: {confidence:.2f})')
    else:
        print('\n未识别到语音内容')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--asr-only':
        if len(sys.argv) < 3:
            print('用法: python test_asr_pipeline.py --asr-only <audio.wav>')
            sys.exit(1)
        asyncio.run(test_asr_only(sys.argv[2]))
    else:
        audio_file = sys.argv[1] if len(sys.argv) > 1 else None
        asyncio.run(test_pipeline(audio_file))
