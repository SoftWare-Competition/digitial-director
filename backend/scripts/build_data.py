"""Build final data files from raw extracted spots and scenic guide text."""
import json

# Approximate GPS coordinates for 灵山胜境 main spots
# Base: 灵山胜境 center = ~31.4300, 120.1150
GPS_COORDS = {
    "LS-001": (31.4280, 120.1180, 40),   # 灵山大照壁 - entrance
    "LS-002": (31.4283, 120.1178, 30),   # 五明桥
    "LS-003": (31.4286, 120.1175, 25),   # 洗心池
    "LS-004": (31.4288, 120.1172, 35),   # 佛足坛
    "LS-005": (31.4292, 120.1168, 30),   # 菩提大道
    "LS-006": (31.4298, 120.1162, 50),   # 九龙灌浴
    "LS-007": (31.4300, 120.1158, 30),   # 降魔浮雕
    "LS-008": (31.4302, 120.1155, 35),   # 阿育王柱
    "LS-009": (31.4303, 120.1150, 30),   # 百子戏弥勒
    "LS-010": (31.4305, 120.1148, 35),   # 祥符禅寺
    "LS-011": (31.4308, 120.1142, 60),   # 灵山大佛
    "LS-012": (31.4305, 120.1140, 40),   # 佛教文化博览馆
    "LS-013": (31.4310, 120.1135, 40),   # 梵宫
    "LS-014": (31.4315, 120.1132, 35),   # 五印坛城
    "LS-015": (31.4313, 120.1130, 30),   # 曼飞龙塔
    "LS-016": (31.4318, 120.1125, 30),   # 无尽意斋
    "NH-001": (31.4220, 120.1080, 50),   # 拈花广场
    "NH-002": (31.4225, 120.1075, 40),   # 梵天花海
    "NH-003": (31.4228, 120.1070, 30),   # 香月花街
    "NH-004": (31.4230, 120.1065, 25),   # 拈花堂
    "NH-005": (31.4232, 120.1060, 40),   # 鹿鸣谷
    "NH-006": (31.4235, 120.1055, 35),   # 鹿鸣谷(dup)
}

# 3 recommended routes from the scenic guide
ROUTES = [
    {
        "id": "ROUTE-001",
        "name": "历史文化深度路线",
        "type": "history",
        "duration_hours": 6.0,
        "description": "适合对佛教文化和历史感兴趣的游客，深度探访灵山千年佛教文化底蕴。",
        "overview_text": "欢迎选择历史文化深度路线！本路线将带您从景区入口开始，依次经过大照壁、五明桥、佛足坛等标志性建筑，深入了解灵山的千年佛教传承。重点探访祥符禅寺的唐代遗风、灵山大佛的庄严宏伟、梵宫的艺术瑰宝和五印坛城的藏传佛教文化。全程约6小时，请合理安排时间。",
        "spots": [
            "LS-001", "LS-002", "LS-003", "LS-004", "LS-005",
            "LS-010", "LS-008", "LS-011", "LS-013", "LS-014"
        ]
    },
    {
        "id": "ROUTE-002",
        "name": "自然风光爱好者路线",
        "type": "nature",
        "duration_hours": 5.0,
        "description": "适合喜爱自然景观和户外漫步的游客，欣赏灵山的湖光山色。",
        "overview_text": "欢迎选择自然风光路线！本路线侧重于灵山胜境的自然之美，从入口开始途经菩提大道的林荫景观、欣赏太湖美景的最佳观景点、灵山大佛的高空全景、以及无尽意斋的园林意境。全程约5小时，记得带好相机记录美景。",
        "spots": [
            "LS-001", "LS-003", "LS-005", "LS-006", "LS-011",
            "LS-015", "LS-016"
        ]
    },
    {
        "id": "ROUTE-003",
        "name": "亲子家庭路线",
        "type": "family",
        "duration_hours": 4.0,
        "description": "适合带小朋友的家庭游客，节奏轻松，互动项目丰富。",
        "overview_text": "欢迎选择亲子家庭路线！本路线节奏轻松，注重互动体验。从九龙灌浴的震撼动态演出开始，到百子戏弥勒的童趣铜像，再到灵山大佛前的"抱佛脚"亲子互动，最后在梵宫欣赏美轮美奂的佛教艺术。全程约4小时，适合全家一起游览。",
        "spots": [
            "LS-001", "LS-006", "LS-009", "LS-011", "LS-013", "LS-014"
        ]
    }
]


def build_spots():
    with open("data/spots_raw.json", "r", encoding="utf-8") as f:
        raw_spots = json.load(f)

    spots = []
    for raw in raw_spots:
        sid = raw["id"]
        coords = GPS_COORDS.get(sid, (31.4300, 120.1150, 30))

        # Gather images placeholder
        images = [
            f"https://cdn.example.com/spots/{sid}_01.jpg",
            f"https://cdn.example.com/spots/{sid}_02.jpg",
        ]

        narration = _build_narration(raw)

        spot = {
            "id": sid,
            "scenic_area": raw["scenic_area"],
            "name": raw["name"],
            "category": _categorize(raw["name"], raw["function_desc"]),
            "lat": coords[0],
            "lng": coords[1],
            "geofence_radius": coords[2],
            "scale": raw["scale"],
            "function_desc": raw["function_desc"],
            "cultural_meaning": raw["cultural_meaning"],
            "detailed_description": raw["detailed_description"],
            "photo_spots": raw["photo_spots"],
            "visitor_info": raw["visitor_info"],
            "images": images,
            "narration_text": narration,
            "narration_audio_url": f"http://localhost:8000/static/audio/{sid}.mp3",
            "narration_duration": _estimate_duration(narration),
            "sort_order": int(sid.split("-")[1]) if sid.startswith("LS-") else 50 + int(sid.split("-")[1]),
            "is_active": 1,
        }
        spots.append(spot)

    with open("data/spots.json", "w", encoding="utf-8") as f:
        json.dump(spots, f, ensure_ascii=False, indent=2)
    print(f"Built {len(spots)} spots → data/spots.json")


def build_routes():
    with open("data/routes.json", "w", encoding="utf-8") as f:
        json.dump(ROUTES, f, ensure_ascii=False, indent=2)
    print(f"Built {len(ROUTES)} routes → data/routes.json")


def build_knowledge_base():
    kb = {
        "景区概况": {
            "名称": "灵山胜境",
            "级别": "国家5A级旅游景区",
            "位置": "江苏省无锡市滨湖区马山镇灵山路",
            "面积": "约30万平方米",
            "简介": "灵山胜境位于无锡太湖国家旅游度假区内，地处马山半岛，三面环湖，是国家5A级旅游景区和世界佛教论坛永久会址。",
            "历史渊源": "灵山胜境的历史可追溯至1300多年前的唐代。唐代玄奘法师自天竺取经归来，途经灵山时赞其'层峦叠翠、山形如印'，赐名'小灵山'。此后千年间寺庙历经兴废，1994年起重建复兴，2009年全部建成开放。",
        },
        "核心景点": {
            "灵山大佛": "高88米，为世界最大的青铜立佛像之一，重达700余吨。佛像面朝太湖，背靠小灵山，庄严宏伟。216级台阶象征108个烦恼和108个愿望。",
            "九龙灌浴": "高27.2米的大型动态群雕，展现释迦牟尼诞生场景。每日定时演出，太子佛周身九龙喷水，场面壮观。",
            "梵宫": "被誉为'东方的卢浮宫'，集佛教艺术之大成。内部汇集敦煌壁画、木雕、琉璃、彩灯等传统工艺，同时融入声光电现代科技。",
            "五印坛城": "汉藏佛教文化交流的见证，以藏式建筑为主体，展示藏传佛教艺术瑰宝。",
            "祥符禅寺": "千年古刹，始建于唐代，现存建筑为清代重建，是灵山胜境历史最悠久的建筑。",
        },
        "实用信息": {
            "开放时间": "全年开放，夏季7:00-17:30，冬季7:30-17:00",
            "门票": "成人票210元，学生半价，60岁以上老人半价",
            "建议游览时间": "4-6小时",
            "最佳季节": "春秋两季（3-5月、9-11月）",
            "交通": "无锡市区乘坐88路/89路公交可直达，或乘坐地铁2号线至'梅园'站后打车约30分钟。",
        }
    }

    with open("data/knowledge_base.json", "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)
    print("Built knowledge base → data/knowledge_base.json")


def build_tips_rules():
    rules = {
        "rules": [
            {
                "id": "uv_high",
                "condition": {"type": "weather", "field": "uv_index", "operator": "gt", "value": 6},
                "tip": {"type": "weather", "priority": "high", "icon": "sun", "title": "防晒提醒", "text": "今日紫外线指数较高，建议佩戴遮阳帽和涂抹防晒霜。"}
            },
            {
                "id": "rain_soon",
                "condition": {"type": "weather", "field": "precip_probability_2h", "operator": "gt", "value": 60},
                "tip": {"type": "weather", "priority": "high", "icon": "rain", "title": "降雨提醒", "text": "预计未来两小时可能有雨，建议就近避雨或准备雨具。"}
            },
            {
                "id": "late_afternoon",
                "condition": {"type": "composite", "operator": "and", "conditions": [
                    {"type": "time", "field": "hour", "operator": "gte", "value": 16},
                ]},
                "tip": {"type": "time", "priority": "medium", "icon": "clock", "title": "时间提醒", "text": "距离景区闭园还有一段时间，建议合理规划剩余游览路线。"}
            },
            {
                "id": "hot_weather",
                "condition": {"type": "weather", "field": "temperature", "operator": "gt", "value": 35},
                "tip": {"type": "weather", "priority": "medium", "icon": "hot", "title": "高温提醒", "text": "天气炎热，请注意防暑降温，多补充水分。前方有休息区和饮水点。"}
            },
            {
                "id": "winter_warm",
                "condition": {"type": "composite", "operator": "and", "conditions": [
                    {"type": "weather", "field": "temperature", "operator": "lt", "value": 5},
                ]},
                "tip": {"type": "weather", "priority": "medium", "icon": "cold", "title": "保暖提醒", "text": "当前气温较低，请注意保暖。灵山湖边风大，建议佩戴帽子围巾。"}
            },
        ]
    }

    with open("data/tips_rules.json", "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    print("Built tips rules → data/tips_rules.json")


def _build_narration(raw: dict) -> str:
    name = raw["name"]
    loc = raw.get("location", "")
    scale = raw.get("scale", "")
    func = raw.get("function_desc", "")
    culture = raw.get("cultural_meaning", "")

    return f"欢迎来到{name}！{name}位于{loc}。{scale}。{func}。{culture}"


def _categorize(name: str, func_desc: str) -> str:
    keywords_map = {
        "建筑景观": ["照壁", "桥", "门", "塔", "宫", "城", "堂", "坊", "碑", "柱", "亭"],
        "自然景观": ["大道", "海", "谷", "林", "花", "湖", "山"],
        "文化景观": ["池", "浮雕", "佛像", "雕塑", "广场", "街", "博"],
    }
    for cat, keywords in keywords_map.items():
        for kw in keywords:
            if kw in name or kw in func_desc:
                return cat
    return "文化景观"


def _estimate_duration(text: str) -> int:
    """Estimate narration duration: ~3 chars per second for Chinese TTS."""
    chars = len(text.replace("\n", "").replace(" ", ""))
    return max(30, min(300, chars // 3))


if __name__ == "__main__":
    build_spots()
    build_routes()
    build_knowledge_base()
    build_tips_rules()
    print("\nDone. All data files built.")
