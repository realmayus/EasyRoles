import firebase_admin
from firebase_admin import credentials, firestore

quit(1)

firebase_cred = credentials.Certificate("firebase-sdk.json")  # Obtaining certificate from ./firebase-sdk.json
firebase_admin.initialize_app(firebase_cred)  # Initializing firebase app with credentials
db = firestore.client()

count = 0
for col in db.collections():
    print(str(col.id))
    for doc in col.stream():
        if "message" not in doc._data:
            continue
        db.collection(col.id).document(doc.id).set({
            "roles": [{
                "message": doc.get("message"),
                "emoji": doc.get("emoji"),
                "mention_id": doc.get("mention_id")
            }]
        }, merge=True)

    count += 1

print(f"Count: {count}")


# last three:
# 932373757744537613
# 932433295537479693
# 932434301566464040
