"""DeepSeek Chat API client with intelligent knowledge retrieval (RAG)."""
import json
import httpx

from app.config import settings

# Knowledge Base (lazy-loaded, cached)
_kb_cache = None


def _load_kb() -> dict:
    global _kb_cache
    if _kb_cache is not None:
        return _kb_cache
    try:
        with open("data/knowledge_base.json", "r", encoding="utf-8") as f:
            _kb_cache = json.load(f)
    except Exception:
        _kb_cache = {
            "景区概况": {"简介": "灵山胜境，国家5A级景区，位于无锡太湖之滨。"},
            "核心景点": {},
            "常见问答": {},
        }
    return _kb_cache


def _retrieve_knowledge(user_question: str, spot_context: str = "") -> str:
    """Retrieve relevant knowledge chunks based on the user's question."""
    kb = _load_kb()
    q = user_question
    chunks = []

    # 1. FAQ
    faq = kb.get("常见问答", {})
    for q_key, answer in faq.items():
        keywords = q_key.replace("灵山", "").replace("胜境", "").strip()
        kw_parts = [c for c in keywords if c not in "??,。."]
        if len(kw_parts) >= 2:
            match_count = sum(1 for c in kw_parts if c in q)
            if match_count >= len(kw_parts) * 0.4:
                chunks.append(f"FAQ: {q_key} - {answer[:300]}")

    # 2. Overview
    overview_kw = ["历史", "由来", "起源", "背景", "选址", "在哪", "什么时候建", "创建", "面积", "多大", "5a", "a级", "级别", "概况", "简介", "介绍"]
    if any(kw in q for kw in overview_kw):
        ov = kb.get("景区概况", {})
        for key in ["简介", "历史渊源", "现代复兴"]:
            if ov.get(key):
                chunks.append(f"景区概况-{key}: {ov[key][:400]}")

    # 3. Cultural
    culture_kw = ["文化", "佛教", "禅", "意义", "内涵", "艺术", "传统", "工艺"]
    if any(kw in q for kw in culture_kw):
        cul = kb.get("文化内涵", {})
        for key, val in cul.items():
            if val:
                chunks.append(f"文化-{key}: {val[:300]}")

    # 4. Spot matching
    spots = kb.get("核心景点", {})
    for name, info in spots.items():
        if name in q or any(c in q for c in name[:3]):
            detail = info.get("详细介绍", "") or info.get("文化内涵", "")
            chunks.append(f"景点-{name}: {detail[:400]}")
            if info.get("参观信息"):
                chunks.append(f"{name}-参观: {info['参观信息'][:200]}")

    # 5. Spot context
    if spot_context:
        chunks.insert(0, f"当前位置: {spot_context[:500]}")

    # 6. Overview always
    ov = kb.get("景区概况", {})
    if ov.get("简介"):
        chunks.append(f"景区简介: {ov['简介'][:200]}")

    # 7. Routes
    route_kw = ["路线", "怎么走", "游览", "游玩", "推荐", "行程", "攻略", "带孩", "家庭", "老", "几小时"]
    if any(kw in q for kw in route_kw):
        routes = kb.get("游览路线", {})
        for key, val in routes.items():
            if val:
                chunks.append(f"路线-{key}: {val[:400]}")

    # 8. Practical info
    practical_kw = ["时间", "几点", "开门", "关门", "住", "酒店", "吃", "穿", "门票", "票价", "多少钱", "停车", "交通", "公交", "地铁", "自驾"]
    if any(kw in q for kw in practical_kw):
        pi = kb.get("实用信息", {})
        for key, val in pi.items():
            if val:
                chunks.append(f"实用-{key}: {val[:400]}")

    # Deduplicate
    seen = set()
    unique = []
    for c in chunks:
        sig = c[:60]
        if sig not in seen:
            seen.add(sig)
            unique.append(c)

    result = "\n\n".join(unique)
    return result[:3000] if result else "灵山胜境是国家5A级景区，位于无锡太湖之滨。"


SYSTEM_PROMPT = """你是灵山胜境的AI数字人导游，名字叫"小灵"。

## 身份
灵山胜境专属导游，热情亲切，说话像朋友，简洁精炼（每次150字以内），适合语音播报。

## 知识库（必须严格依据以下信息回答，不要编造）
{knowledge_base}

## 当前位置
{spot_context}

## 对话历史
{conversation_history}

## 规则
1. 知识库有答案的，直接引用，可加趣味细节
2. 知识库没覆盖的，诚实说"小灵还在学习"，不要编造
3. 佛教文化要通俗易懂，不枯燥
4. 多引导实地体验
5. 回答控制在150字以内"""


async def chat(
    user_message: str,
    spot_context: str = "",
    conversation_history: list[dict] = None,
) -> str:
    """Send message to DeepSeek and get response."""
    if not settings.deepseek_api_key:
        return _clean_answer(_fallback_response(user_message, spot_context))

    knowledge_text = _retrieve_knowledge(user_message, spot_context)

    hist_text = ""
    if conversation_history:
        for msg in conversation_history[-5:]:
            role = "游客" if msg.get("role") == "user" else "小灵"
            text = msg.get("text", "")[:100]
            hist_text += f"{role}: {text}\n"

    system_prompt = SYSTEM_PROMPT.format(
        knowledge_base=knowledge_text,
        spot_context=spot_context or "暂无精确位置信息",
        conversation_history=hist_text or "这是游客的第一个问题",
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.deepseek_base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.deepseek_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 400,
                },
            )
            result = resp.json()
            return _clean_answer(result["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"[LLM] Error: {e}")
        return _clean_answer(_fallback_response(user_message, spot_context))


def _clean_answer(text: str) -> str:
    """Remove stage directions, emotes, filler from AI responses."""
    import re
    # Remove all content in Chinese/English parentheses that are actions/stage directions
    # Matches: （笑）, (哈哈), （稍作停顿）, (停顿片刻), （指向大佛）, (轻咳) etc
    action_keys = '笑|哈|呵|嘻|嘿|嗯|哦|哎|咦|呜|啦|吧|呢|呀|哼|停|顿|稍|咳|清|指|转|回|看|望|观|察|示|意|点|摇|摆|眨|叹|呼|吸|走|跑|跳|坐|站|挥|拍|鼓|掌|想|思|考|念|微|温|亲|热|冷|轻|重|快|慢|大|小|高|低|远|近|渐|缓|突|猛|忽'
    text = re.sub(r'[（(][^）)]*?(?:' + action_keys + r')[^）)]*?[）)]', '', text)
    # Clean up extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _fallback_response(question: str, spot_context: str) -> str:
    """Fallback when LLM unavailable."""
    q = question
    kb = _load_kb()

    # FAQ match
    faq = kb.get("常见问答", {})
    for q_key, answer in faq.items():
        kw_parts = [c for c in q_key if c not in "??,。."]
        if len(kw_parts) >= 3:
            match_count = sum(1 for c in kw_parts if c in q)
            if match_count >= len(kw_parts) * 0.5:
                return answer[:200]

    # Keyword match
    keyword_map = {
        "大佛": "灵山大佛高88米，重700余吨。右手施无畏印，左手结与愿印。推荐登216级台阶抱佛脚！",
        "门票": "成人票210元，学生和60-69岁老人105元，70岁以上免票。",
        "时间": "夏季7:00-17:30，冬季7:30-17:00。",
        "九龙": "九龙灌浴每天10:00、11:30、13:30、15:00各一场，每场约15分钟。",
        "梵宫": "灵山梵宫被誉为'东方的卢浮宫'，是佛教论坛永久会址。",
        "路线": "推荐中轴线：大照壁->五明桥->九龙灌浴->大佛->梵宫->五印坛城，约4-6小时。",
    }
    for kw, ans in keyword_map.items():
        if kw in q:
            return ans

    # Spot match
    spots = kb.get("核心景点", {})
    for name, info in spots.items():
        if name in q:
            detail = info.get("详细介绍", "") or info.get("文化内涵", "")
            return f"关于{name}：{detail[:200]}"

    if spot_context:
        return f"{spot_context[:150]}"

    return "感谢您的提问！我是灵山胜境的AI导游小灵，您可以问我关于景点历史、游览路线、开放时间等各种问题。"
