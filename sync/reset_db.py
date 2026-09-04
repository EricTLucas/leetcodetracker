import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
load_dotenv()

with open("firebase-service-account.json", "r") as f:
    service_account_info = json.load(f)

USERNAME = "EricLucas"

cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)
db = firestore.client()

def delete_collection(coll_ref, batch_size=50):
    while True:
        docs = list(coll_ref.limit(batch_size).stream())
        if not docs:
            break

        for doc in docs:
            for subcoll in doc.reference.collections():
                delete_collection(subcoll, batch_size)

            doc.reference.delete()


def delete_root_collection(root_ref, doc_ids):
    for doc_id in doc_ids:
        doc_ref = root_ref.document(doc_id)

        # Delete all subcollections of this document
        for subcoll in doc_ref.collections():
            delete_collection(subcoll)

        # Delete the document itself
        doc_ref.delete()



def wipe_firestore(db):
    print("Wiping Firestore database...")
    delete_root_collection(
        db.collection("leetcode"),
        ["submissions", "stats", "recent", "problems"]
    )

    print("Firestore wipe complete.")


if __name__ == "__main__":
    wipe_firestore(db)