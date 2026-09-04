import time
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from datetime import datetime, UTC

with open("firebase-service-account.json", "r") as f:
    service_account_info = json.load(f)

USERNAME = "EricLucas"

cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)
db = firestore.client()

def firestore_ping(db):
    try:
        doc = db.collection("_ping").document("ping").get(field_paths=[])
        print("Firestore connection successful.")
        return
    except Exception as e:
        print("Firestore connection failed:", e)
        return


def init_db():
    firestore_ping(db)
    doc = db.collection("leetcode").document("stats").get()

    if not doc.exists:
        db.collection("leetcode").document("stats").set({
            "total_unique_solved": 0,
            "solved_week": 0,
            "full_sync_done": "false",
            "last_sync": datetime.now(UTC).isoformat()
         })


def save_submission(sub):
    db.collection("leetcode").document("submissions").collection("items").document(sub["title_slug"]).set(sub)

def get_per_score(slug):
    doc = db.collection("leetcode").document("submissions").collection("items").document(slug).get()
    if doc.exists:
        data = doc.to_dict()
        return int(float(data.get("runtime_percentile").rstrip("%")))  + int(float(data.get("memory_percentile").rstrip("%")))
    return None

def save_problem(slug, completed):
    db.collection("leetcode").document("problems").collection("items").document(slug).set({
        "completed": completed
    })
   
def get_meta(key):
    doc = db.collection("leetcode").document("stats").get()
    return doc.get(key) if doc.exists else None

def set_meta(key, value):
    db.collection("leetcode").document("stats").update({key: value})

def get_known_slugs():
    sub = db.collection("leetcode").document("problems").collection("items")
    docs = sub.stream()
    return {doc.id for doc in docs}

def toTitle(slug):
    words = slug.split("-")
    return " ".join(word.capitalize() for word in words)

def push_recent_to_firebase(recent):
    batch = db.batch()
    col = db.collection("leetcode").document("recent").collection("items")

    for sub in recent:
        doc = col.document(sub["titleSlug"])
        batch.set(doc, sub)

    batch.commit()
    print("Pushed recent submissions to Firebase.")

def push_stats_to_firebase(total_unique, solved_week):
    db.collection("leetcode").document("stats").set({
        "total_unique_solved": total_unique,
        "solved_week": solved_week,
        "last_sync": datetime.now(UTC).isoformat(),
        "full_sync_done": "true"
    })
    print("Pushed stats to Firebase.")