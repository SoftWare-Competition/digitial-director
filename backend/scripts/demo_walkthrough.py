"""Simulate a complete mini-program user journey through API calls."""
import json
import urllib.request

BASE = "http://localhost:8000/api/v1"


def api(method, path, data=None):
    url = f"{BASE}{path}"
    body = None
    if data:
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def hdr(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ============================================================
# Step 1: User opens mini program → auto login
# ============================================================
hdr("STEP 1: 用户打开小程序 → 自动登录")
result = api("POST", "/user/login", {"code": "wx_test_visitor_001"})
user = result["data"]["user"]
token = result["data"]["token"]
print(f"  欢迎游客: {user['nickname']}")
print(f"  Token: {token[:30]}...")

# ============================================================
# Step 2: Home page loads → get tips
# ============================================================
hdr("STEP 2: 首页加载 → 获取智能提示")
result = api("GET", "/tips/current")
tips = result["data"]["tips"]
if tips:
    for t in tips:
        print(f"  [{t['priority'].upper()}] {t['title']}: {t['text']}")
else:
    print("  暂无特殊提示（天气良好，时间宽裕）")

# ============================================================
# Step 3: User browses routes → selects one
# ============================================================
hdr("STEP 3: 浏览路线 → 选择「历史文化深度路线」")
result = api("GET", "/routes")
routes = result["data"]["routes"]
for r in routes:
    print(f"  [{r['type']}] {r['name']} ({r['duration_hours']}h, {r['spot_count']}个景点)")

# Select route 1
result = api("GET", "/routes/ROUTE-001")
route = result["data"]
print(f"\n  已选择: {route['name']}")
print(f"  路线景点顺序:")
for s in route["spots"]:
    print(f"    {s['sequence']}. {s['name']}")

# ============================================================
# Step 4: User opens map → GPS tracking starts
# ============================================================
hdr("STEP 4: 打开地图 → GPS 实时追踪已开启")
print("  [小程序调用 wx.startLocationUpdateBackground]")
print("  [每10秒上报GPS坐标到 /narration/checkin]")

# ============================================================
# Step 5: User walks to 灵山大照壁 → auto narration triggers
# ============================================================
hdr("STEP 5: 游客走近「灵山大照壁」→ 自动触发讲解")
spot_coords = [
    (31.4280, 120.1180, "灵山大照壁"),
    (31.4283, 120.1178, "五明桥"),
    (31.4298, 120.1162, "九龙灌浴"),
    (31.4308, 120.1142, "灵山大佛"),
]

for lat, lng, name in spot_coords:
    result = api("POST", "/narration/checkin", {"lat": lat, "lng": lng})
    data = result["data"]
    if data["matched"]:
        spot = data["spot"]
        narration = data["narration"]
        print(f"\n  📍 到达: {spot['name']}")
        print(f"  🔊 自动播放讲解 (时长 {narration['duration_sec']}秒)")
        print(f"  📝 讲解片段: {narration['text'][:120]}...")
        if narration["is_repeat"]:
            print(f"  ⚠️ 30分钟内已播过，跳过重复")
    else:
        print(f"\n  ❌ {name}: 不在范围内")

# ============================================================
# Step 6: User taps a marker → spot detail page
# ============================================================
hdr("STEP 6: 点击「灵山大佛」标记 → 景点详情页")
result = api("GET", "/spots/LS-011")
spot = result["data"]
print(f"  🏷 名称: {spot['name']}")
print(f"  📐 规模: {spot['scale'][:80]}...")
print(f"  🕐 参观: {spot.get('visitor_info', 'N/A')[:60]}")
print(f"  🎵 讲解音频: {spot.get('narration_audio_url', 'N/A')}")

# ============================================================
# Step 7: User presses "ask question" → goes to digital human
# ============================================================
hdr("STEP 7: 在「灵山大佛」前按住说话 → 语音问答")

# Simulate audio upload (use a small dummy file)
# We'll use a text-based approach to show the Q&A logic
print("  🎤 用户按住按钮: '灵山大佛有多高？'")
print("  ⏳ [录音中...松开发送]")

# Create a tiny mp3 placeholder
import tempfile, os
tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
tmp.write(b"\xff\xfb\x90\x00" * 500)  # Minimal MP3-like bytes
tmp.close()

import subprocess
curl_cmd = f'curl -s -X POST {BASE}/qa/ask -F "audio=@{tmp.name}" -F "lat=31.4308" -F "lng=120.1142"'
result_bytes = subprocess.check_output(curl_cmd, shell=True)
result = json.loads(result_bytes)
os.unlink(tmp.name)

qa = result["data"]
print(f"\n  👤 用户说: {qa['question_text']}")
print(f"  🤖 小灵回答: {qa['answer_text']}")
print(f"  🔊 回答音频: {'已生成' if qa.get('answer_audio_url') else '使用TTS合成中...'}")
print(f"  📋 会话ID: {qa['session_id']}")

# ============================================================
# Step 8: Check profile → history
# ============================================================
hdr("STEP 8: 个人中心 → 查看游览记录")
result = api("GET", "/user/history")
history = result["data"]
print(f"  🏁 签到数: {len(history['checkins'])} 个景点")
for c in history["checkins"][-5:]:
    print(f"    📍 {c['spot_name']} ({c['trigger_type']}) - {c['created_at'][:19]}")
print(f"  💬 问答会话: {len(history['qa_sessions'])} 次")

# ============================================================
# Summary
# ============================================================
hdr("游览流程演示完成")
print("""
  以上 8 个步骤模拟了小程序的完整用户旅程：

  1. 登录          → POST /user/login
  2. 首页加载      → GET /tips/current
  3. 选择路线      → GET /routes → GET /routes/ROUTE-001
  4. GPS开始追踪   → 小程序端持续轮询
  5. 自动讲解触发  → POST /narration/checkin (每10秒)
  6. 景点详情      → GET /spots/LS-011
  7. 语音问答      → POST /qa/ask (按住说话)
  8. 个人中心      → GET /user/history

  全部 API 已跑通，后端响应正常 ✅
""")
