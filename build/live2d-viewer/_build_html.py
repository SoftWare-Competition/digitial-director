import os

CSS = """*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#1a6d4c;width:100vw;height:100vh;display:flex;flex-direction:column;overflow:hidden;-webkit-user-select:none;user-select:none}
.char-area{height:45vh;background:linear-gradient(180deg,#1a6d4c 0%,#228b5e 100%);position:relative;flex-shrink:0}
.char-area canvas{display:block;width:100%;height:100%}
.char-status{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);color:#fff;font-size:12px;background:rgba(0,0,0,0.4);padding:4px 14px;border-radius:12px;pointer-events:none;transition:opacity .3s;z-index:5}
.chat-area{flex:1;background:#f0f2f5;overflow-y:auto;padding:12px 16px;-webkit-overflow-scrolling:touch}
.chat-empty{display:flex;flex-direction:column;align-items:center;padding-top:40px;color:#999}
.chat-empty .icon{font-size:48px;margin-bottom:12px}
.chat-empty .text{font-size:15px;margin-bottom:6px}
.chat-empty .hint{font-size:13px;color:#bbb}
.msg-row{display:flex;margin-bottom:14px}
.msg-row.user{justify-content:flex-end}
.msg-row.assistant{justify-content:flex-start}
.msg-bubble{max-width:78%;padding:10px 14px;border-radius:14px;font-size:14px;line-height:1.6;word-break:break-word;white-space:pre-wrap}
.msg-bubble.user{background:#1a6d4c;color:#fff;border-bottom-right-radius:4px}
.msg-bubble.assistant{background:#fff;color:#333;border-bottom-left-radius:4px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.typing-dots{display:flex;gap:4px;padding:4px 0}
.typing-dots span{width:6px;height:6px;border-radius:50%;background:#aaa;animation:blink 1.4s infinite}
.typing-dots span:nth-child(2){animation-delay:.2s}
.typing-dots span:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,60%,100%{opacity:.2}30%{opacity:1}}
.bottom-bar{background:#fff;border-top:1px solid #eee;padding:10px 14px;padding-bottom:calc(10px + env(safe-area-inset-bottom));flex-shrink:0}
.text-row{display:flex;gap:10px;align-items:center;margin-bottom:10px}
.text-inp{flex:1;height:36px;background:#f5f5f5;border:none;outline:none;border-radius:18px;padding:0 14px;font-size:14px;color:#333}
.text-inp::placeholder{color:#bbb}
.btn-send{width:56px;height:32px;line-height:32px;text-align:center;background:#ccc;color:#fff;border-radius:16px;font-size:13px;cursor:pointer;border:none;transition:background .2s}
.btn-send.active{background:#1a6d4c}
.btn-send:disabled{opacity:.5}
.voice-row{width:100%}
.btn-voice{width:100%;height:44px;line-height:44px;text-align:center;background:#1a6d4c;color:#fff;border-radius:22px;font-size:15px;cursor:pointer;border:none;display:flex;align-items:center;justify-content:center;gap:8px}
.btn-voice.recording{background:#e74c3c;animation:pulse .8s infinite}
.btn-voice:disabled{background:#ccc;color:#999}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.8}}"""

print('CSS constant written, length:', len(CSS))
