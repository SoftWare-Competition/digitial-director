import json, os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models import ScenicSpot, Route, RouteSpot
from app.routers import spots, narration, qa, tips, user, weather

# 项目根目录 (lingshan-tour-guide/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def seed_if_empty():
    """If scenic_spots table is empty, seed from data/*.json"""
    db = SessionLocal()
    try:
        existing = db.query(ScenicSpot).first()
        if existing:
            print(f"[DB] Already has {db.query(ScenicSpot).count()} spots, skip seed")
            return

        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        spots_path = os.path.join(data_dir, "spots.json")
        routes_path = os.path.join(data_dir, "routes.json")

        if not os.path.exists(spots_path):
            print(f"[DB] spots.json not found at {spots_path}, skip seed")
            return

        with open(spots_path, "r", encoding="utf-8") as f:
            spots_data = json.load(f)
        for s in spots_data:
            spot = ScenicSpot(
                id=s["id"],
                scenic_area=s.get("scenic_area", "灵山胜境"),
                name=s["name"],
                category=s.get("category", ""),
                lat=s["lat"],
                lng=s["lng"],
                geofence_radius=s.get("geofence_radius", 30),
                scale=s.get("scale", ""),
                function_desc=s.get("function_desc", ""),
                cultural_meaning=s.get("cultural_meaning", ""),
                detailed_description=s.get("detailed_description", ""),
                photo_spots=s.get("photo_spots", ""),
                visitor_info=s.get("visitor_info", ""),
                images=json.dumps(s.get("images", [])),
                narration_text=s.get("narration_text", ""),
                narration_audio_url=s.get("narration_audio_url", ""),
                narration_duration=s.get("narration_duration", 0),
                sort_order=s.get("sort_order", 0),
                is_active=s.get("is_active", 1),
            )
            db.add(spot)
        print(f"[DB] Seeded {len(spots_data)} scenic spots from spots.json")

        if os.path.exists(routes_path):
            with open(routes_path, "r", encoding="utf-8") as f:
                routes_data = json.load(f)
            for r in routes_data:
                route = Route(
                    id=r["id"],
                    name=r["name"],
                    type=r["type"],
                    duration_hours=r["duration_hours"],
                    description=r.get("description", ""),
                    overview_text=r.get("overview_text", ""),
                    overview_audio_url=r.get("overview_audio_url", ""),
                )
                db.add(route)
                db.flush()
                for seq, spot_id in enumerate(r["spots"], 1):
                    rs = RouteSpot(route_id=route.id, spot_id=spot_id, sequence=seq)
                    db.add(rs)
            print(f"[DB] Seeded {len(routes_data)} routes from routes.json")

        db.commit()
        print("[DB] Auto-seed complete!")
    except Exception as e:
        db.rollback()
        print(f"[DB] Seed error: {e}")
        raise
    finally:
        db.close()


def _migrate_schema():
    """SQLite schema migration: add columns/tables that don't exist yet."""
    import sqlite3
    # Resolve relative path to absolute (same logic as SQLAlchemy)
    db_rel = settings.database_url.replace("sqlite:///", "")
    if not os.path.isabs(db_rel):
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), db_rel)
    else:
        db_path = db_rel
    print(f"[DB Migration] Using database at: {db_path}")
    conn = sqlite3.connect(db_path)

    # 1. Add email column to users if not exists
    cols = [row[1] for row in conn.execute("PRAGMA table_info(users)")]
    if "email" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN email VARCHAR(128)")
        try: conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email)")
        except: pass
        print("[DB Migration] Added 'email' column to users table")
    if "username" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN username VARCHAR(64)")
        try: conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users(username)")
        except: pass
        print("[DB Migration] Added 'username' column to users table")
    if "password_hash" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(256)")
        print("[DB Migration] Added 'password_hash' column to users table")

    # 2. Create email_verification_codes table if not exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(128) NOT NULL,
            code VARCHAR(6) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            is_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_email_vc_email ON email_verification_codes(email)")
    print("[DB Migration] email_verification_codes table ready")

    conn.commit()
    conn.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_schema()
    seed_if_empty()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI数字人导游 API",
    description="灵山胜境 AI 数字人导游系统 MVP",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/audio", StaticFiles(directory=os.path.join(BASE_DIR, "backend", "audio")), name="static_audio")
app.mount("/static/model", StaticFiles(directory=os.path.join(BASE_DIR, "backend", "static", "model")), name="static_model")
app.mount("/static/avatars", StaticFiles(directory=os.path.join(BASE_DIR, "backend", "static", "avatars")), name="static_avatars")
app.mount("/live2d-viewer/static", StaticFiles(directory=os.path.join(BASE_DIR, "build", "live2d-viewer")), name="live2d_viewer_static")

from fastapi.responses import HTMLResponse
import os

@app.get("/live2d-viewer", response_class=HTMLResponse)
@app.get("/live2d-viewer/", response_class=HTMLResponse)
async def live2d_viewer():
    html_path = os.path.join(os.path.dirname(__file__), "..", "..", "build", "live2d-viewer", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

app.include_router(user.router, prefix="/api/v1", tags=["用户"])
app.include_router(spots.router, prefix="/api/v1", tags=["景点与路线"])
app.include_router(narration.router, prefix="/api/v1", tags=["讲解触发"])
app.include_router(qa.router, prefix="/api/v1", tags=["语音问答"])
app.include_router(tips.router, prefix="/api/v1", tags=["智能提示"])
app.include_router(weather.router, prefix="/api/v1", tags=["天气"])


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/v1/admin/reseed")
def force_reseed():
    """强制从 JSON 重新灌入数据，会更新已有记录"""
    db = SessionLocal()
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        spots_path = os.path.join(data_dir, "spots.json")

        with open(spots_path, "r", encoding="utf-8") as f:
            spots_data = json.load(f)

        updated = 0
        for s in spots_data:
            spot = db.query(ScenicSpot).filter(ScenicSpot.id == s["id"]).first()
            if spot:
                spot.name = s["name"]
                spot.category = s.get("category", "")
                spot.lat = s["lat"]
                spot.lng = s["lng"]
                spot.geofence_radius = s.get("geofence_radius", 30)
                spot.scale = s.get("scale", "")
                spot.cultural_meaning = s.get("cultural_meaning", "")
                spot.detailed_description = s.get("detailed_description", "")
                spot.visitor_info = s.get("visitor_info", "")
                spot.narration_text = s.get("narration_text", "")
                spot.is_active = s.get("is_active", 1)
                updated += 1

        db.commit()
        return {"status": "ok", "message": f"Updated {updated} spots from spots.json"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
