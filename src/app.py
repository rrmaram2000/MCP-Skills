"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi import Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import json
from typing import Dict, Any

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

DATA_DIR = current_dir / "data"
DATA_FILE = DATA_DIR / "activities.json"


def _ensure_data_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def _load_activities() -> Dict[str, Dict[str, Any]]:
    _ensure_data_file()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Ensure default structure for legacy entries
    for name, details in data.items():
        details.setdefault("participants", [])
        details.setdefault("max_participants", 0)
        details.setdefault("draft", False)
    return data


def _save_activities(activities: Dict[str, Dict[str, Any]]):
    _ensure_data_file()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(activities, f, indent=2)


# Load activities from disk on startup
activities = _load_activities()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities(published_only: bool = True):
    if not published_only:
        return activities
    # Return only non-draft (published) activities
    return {name: details for name, details in activities.items() if not details.get("draft", False)}


@app.get("/activities/all")
def get_all_activities():
    # Admin/host view: include drafts
    return activities


@app.post("/activities")
def create_activity(payload: Dict[str, Any] = Body(...)):
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Missing 'name' field")
    if name in activities:
        raise HTTPException(status_code=400, detail="Activity already exists")

    activities[name] = {
        "description": payload.get("description", ""),
        "schedule": payload.get("schedule", ""),
        "max_participants": int(payload.get("max_participants", 0)),
        "participants": payload.get("participants", []),
        "poster": payload.get("poster"),
        "draft": bool(payload.get("draft", True)),
    }
    _save_activities(activities)
    return {"message": f"Created activity '{name}'", "activity": activities[name]}


@app.put("/activities/{activity_name}")
def update_activity(activity_name: str, payload: Dict[str, Any] = Body(...)):
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")
    activity = activities[activity_name]
    for key in ["description", "schedule", "max_participants", "poster"]:
        if key in payload:
            activity[key] = payload[key] if key != "max_participants" else int(payload[key])
    if "draft" in payload:
        activity["draft"] = bool(payload["draft"])
    _save_activities(activities)
    return {"message": f"Updated activity '{activity_name}'", "activity": activity}


@app.delete("/activities/{activity_name}")
def delete_activity(activity_name: str):
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")
    removed = activities.pop(activity_name)
    _save_activities(activities)
    return {"message": f"Deleted activity '{activity_name}'", "activity": removed}


@app.post("/activities/{activity_name}/publish")
def publish_activity(activity_name: str):
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")
    activities[activity_name]["draft"] = False
    _save_activities(activities)
    return {"message": f"Published activity '{activity_name}'"}


@app.post("/activities/{activity_name}/unpublish")
def unpublish_activity(activity_name: str):
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")
    activities[activity_name]["draft"] = True
    _save_activities(activities)
    return {"message": f"Unpublished activity '{activity_name}'"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    _save_activities(activities)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    _save_activities(activities)
    return {"message": f"Unregistered {email} from {activity_name}"}
