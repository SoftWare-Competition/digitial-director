"""Build all data files from raw extracted spots."""
import json
import sys
import os

os.chdir(os.path.join(os.path.dirname(__file__), ".."))

# Load raw spots
with open("data/spots_raw.json", "r", encoding="utf-8") as f:
    raw_spots = json.load(f)

GPS_COORDS = {
    "LS-001": (31.4280, 120.1180, 40),
    "LS-002": (31.4283, 120.1178, 30),
    "LS-003": (31.4286, 120.1175, 25),
    "LS-004": (31.4288, 120.1172, 35),
    "LS-005": (31.4292, 120.1168, 30),
    "LS-006": (31.4298, 120.1162, 50),
    "LS-007": (31.4300, 120.1158, 30),
    "LS-008": (31.4302, 120.1155, 35),
    "LS-009": (31.4303, 120.1150, 30),
    "LS-010": (31.4305, 120.1148, 35),
    "LS-011": (31.4308, 120.1142, 60),
    "LS-012": (31.4305, 120.1140, 40),
    "LS-013": (31.4310, 120.1135, 40),
    "LS-014": (31.4315, 120.1132, 35),
    "LS-015": (31.4313, 120.1130, 30),
    "LS-016": (31.4318, 120.1125, 30),
    "NH-001": (31.4220, 120.1080, 50),
    "NH-002": (31.4225, 120.1075, 40),
    "NH-003": (31.4228, 120.1070, 30),
    "NH-004": (31.4230, 120.1065, 25),
    "NH-005": (31.4232, 120.1060, 40),
    "NH-006": (31.4235, 120.1055, 35),
}


def categorize(name, func_desc):
    kw = {
        "建筑": ["照壁", "桥", "门", "塔", "宫", "城",
                         "堂", "坊", "碑", "柱", "亭"],
        "自然": ["大道", "海", "谷", "林", "花", "湖", "山"],
        "文化": ["池", "浮雕", "佛像", "雕塑", "广场",
                        "街", "博"],
    }
    for cat, keywords in kw.items():
        for k in keywords:
            if k in name or k in func_desc:
                return cat
    return "文化景观"


def estimate_duration(text):
    return max(30, min(300, len(text.replace("\n", "").replace(" ", "")) // 3))


spots = []
for raw in raw_spots:
    sid = raw["id"]
    coords = GPS_COORDS.get(sid, (31.4300, 120.1150, 30))
    name = raw["name"]
    loc = raw.get("location", "")
    scale = raw.get("scale", "")
    func = raw.get("function_desc", "")
    culture = raw.get("cultural_meaning", "")
    narration = f"欢迎来到{name}！\n\n{name}位于{loc}\n\n{scale}\n\n{func}\n\n{culture}"

    spot = {
        "id": sid,
        "scenic_area": raw["scenic_area"],
        "name": name,
        "category": categorize(name, func),
        "lat": coords[0],
        "lng": coords[1],
        "geofence_radius": coords[2],
        "scale": scale,
        "function_desc": func,
        "cultural_meaning": culture,
        "detailed_description": raw.get("detailed_description", ""),
        "photo_spots": raw.get("photo_spots", ""),
        "visitor_info": raw.get("visitor_info", ""),
        "images": [f"https://cdn.example.com/spots/{sid}_01.jpg"],
        "narration_text": narration,
        "narration_audio_url": f"http://localhost:8000/static/audio/{sid}.mp3",
        "narration_duration": estimate_duration(narration),
        "sort_order": int(sid.split("-")[1]) if sid.startswith("LS-") else 50 + int(sid.split("-")[1]),
        "is_active": 1,
    }
    spots.append(spot)

with open("data/spots.json", "w", encoding="utf-8") as f:
    json.dump(spots, f, ensure_ascii=False, indent=2)
print(f"Built {len(spots)} spots")

routes = [
    {
        "id": "ROUTE-001",
        "name": "历史文化深度路线",
        "type": "history",
        "duration_hours": 6.0,
        "description": "适合对佛教文化和历史感兴趣的游客，深度探访灵山千年佛教文化底蕴。",
        "overview_text": "欢迎选择历史文化深度路线！本路线将带您从景区入口开始，依次探访灵山大照壁、五明桥、佛足坛等标志性建筑，深入了解灵山的千年佛教传承。全程约6小时。",
        "spots": ["LS-001", "LS-002", "LS-003", "LS-004", "LS-005", "LS-010", "LS-008", "LS-011", "LS-013", "LS-014"]
    },
    {
        "id": "ROUTE-002",
        "name": "自然风光爱好者路线",
        "type": "nature",
        "duration_hours": 5.0,
        "description": "适合喜爱自然景观和户外漫步的游客，欣赏灵山的湖光山色。",
        "overview_text": "欢迎选择自然风光路线！本路线侧重于灵山胜境的自然之美，从入口开始途经菩提大道的林荫景观、欣赏太湖美景、灵山大佛的高空全景、以及无尽意斋的园林意境。全程约5小时。",
        "spots": ["LS-001", "LS-003", "LS-005", "LS-006", "LS-011", "LS-015", "LS-016"]
    },
    {
        "id": "ROUTE-003",
        "name": "亲子家庭路线",
        "type": "family",
        "duration_hours": 4.0,
        "description": "适合带小朋友的家庭游客，节奏轻松，互动项目丰富。",
        "overview_text": "欢迎选择亲子家庭路线！本路线节奏轻松，注重互动体验。从九龙灌浴的震撼动态演出开始，到百子戏弥勒的童趣铜像，再到灵山大佛前的抱佛脚亲子互动，最后在梵宫欣赏美轮美奔的佛教艺术。全程约4小时。",
        "spots": ["LS-001", "LS-006", "LS-009", "LS-011", "LS-013", "LS-014"]
    }
]

with open("data/routes.json", "w", encoding="utf-8") as f:
    json.dump(routes, f, ensure_ascii=False, indent=2)
print(f"Built {len(routes)} routes")

kb = {
    "景区概况": {
        "名称": "灵山胜境",
        "级别": "国家5A级旅游景区",
        "位置": "江苏省无锡市滨湖区马山镇灵山路",
        "面积": "约30万平方米",
        "简介": "灵山胜境位于无锡太湖国家旅游度假区内，地处马山半岛，三面环湖，是国家5A级旅游景区和世界佛教论坛永久会址。",
    }
}

with open("data/knowledge_base.json", "w", encoding="utf-8") as f:
    json.dump(kb, f, ensure_ascii=False, indent=2)
print("Built knowledge base")

print("Done!")
