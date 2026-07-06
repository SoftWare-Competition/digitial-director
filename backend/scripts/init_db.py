"""Initialize database: create tables and seed data from JSON files."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import engine, Base, SessionLocal
from app.models import ScenicSpot, Route, RouteSpot


def init():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        existing = db.query(ScenicSpot).first()
        if existing:
            print("Database already seeded. Skipping.")
            return

        # Load spots
        spots_path = os.path.join(os.path.dirname(__file__), "..", "data", "spots.json")
        if not os.path.exists(spots_path):
            print(f"spots.json not found at {spots_path}. Run build_data.py first.")
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
        print(f"Seeded {len(spots_data)} scenic spots.")

        # Load routes
        routes_path = os.path.join(os.path.dirname(__file__), "..", "data", "routes.json")
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
            print(f"Seeded {len(routes_data)} routes.")

        db.commit()
        print("Database initialization complete!")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init()
