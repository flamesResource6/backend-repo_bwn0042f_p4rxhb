import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import create_document, get_documents, db

app = FastAPI(title="Wellbeing Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Wellbeing Assistant Backend Running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# --------- Simple emotion + risk utilities (demo only, not clinical) ---------
EMOJI_RESPONSES = {
    "joy": "I'm happy to hear that! Want a fun fact or a joke?",
    "sadness": "I'm here with you. Want to try a short breathing exercise together?",
    "anger": "That sounds frustrating. Want to label the feeling and take a 10-second pause?",
    "anxiety": "It’s okay to feel worried. Let's try box breathing: 4-in, 4-hold, 4-out, 4-hold.",
    "neutral": "I’m listening. Tell me more."
}

RISK_KEYWORDS = [
    "suicide", "kill myself", "end it", "die", "self harm", "cut myself", "worthless", "no reason to live"
]

POSITIVE_AFFIRMATIONS = [
    "You are enough, exactly as you are.",
    "Every small step counts. I'm proud of you.",
    "Your feelings matter and so do you.",
]
QUOTES = [
    "In the middle of difficulty lies opportunity. — Albert Einstein",
    "This too shall pass.",
]
JOKES = [
    "Why did the math book look sad? It had too many problems.",
    "What do you call cheese that isn’t yours? Nacho cheese!",
]


def classify_emotion(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["happy", "great", "good", "awesome", "yay", ":)"]):
        return "joy"
    if any(k in t for k in ["sad", "down", "cry", "depressed", ":("]):
        return "sadness"
    if any(k in t for k in ["angry", "mad", "furious", "annoyed"]):
        return "anger"
    if any(k in t for k in ["worried", "anxious", "scared", "nervous", "panic"]):
        return "anxiety"
    return "neutral"


def risk_score(text: str) -> float:
    t = text.lower()
    score = 0.0
    for kw in RISK_KEYWORDS:
        if kw in t:
            score = max(score, 0.85)
    # boost if strong negative words
    if any(k in t for k in ["hopeless", "worthless", "hate myself", "can't go on"]):
        score = max(score, 0.6)
    return min(1.0, score)


class ChatRequest(BaseModel):
    child_id: str = Field(...)
    text: str = Field(...)


class ChatResponse(BaseModel):
    response: str
    emotion: str
    risk_score: float


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    emotion = classify_emotion(req.text)
    score = risk_score(req.text)

    base_reply = EMOJI_RESPONSES.get(emotion, EMOJI_RESPONSES["neutral"])

    if score >= 0.85:
        reply = (
            "I’m really glad you told me. You matter and you deserve help. "
            "I’d like to help you reach a trusted adult or a professional. "
            "If you're in immediate danger, please call your local emergency number. "
            "Would you like me to share a helpful message with your parent now?"
        )
        # record a high-risk event
        create_document("riskevent", {
            "child_id": req.child_id,
            "level": "high",
            "reason": "Text trigger keyword",
            "score": score,
            "occurred_at": datetime.now(timezone.utc)
        })
    elif score >= 0.6:
        reply = (
            "I’m noticing words that sound really hard. "
            + base_reply + " You can also press ‘I need help’ to contact a trusted adult."
        )
        create_document("riskevent", {
            "child_id": req.child_id,
            "level": "medium",
            "reason": "Negative self-talk",
            "score": score,
            "occurred_at": datetime.now(timezone.utc)
        })
    else:
        reply = base_reply

    # store message
    create_document("message", {
        "child_id": req.child_id,
        "text": req.text,
        "emotion": emotion,
        "risk_score": score,
        "response": reply,
    })

    return ChatResponse(response=reply, emotion=emotion, risk_score=score)


@app.get("/api/messages")
def list_messages(child_id: str = Query(...), limit: int = Query(50)):
    docs = get_documents("message", {"child_id": child_id}, limit=limit)
    # serialize ObjectId
    for d in docs:
        d["_id"] = str(d.get("_id"))
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
    return {"items": docs}


@app.get("/api/risk-events")
def list_risk(child_id: str = Query(...), limit: int = Query(50)):
    docs = get_documents("riskevent", {"child_id": child_id}, limit=limit)
    for d in docs:
        d["_id"] = str(d.get("_id"))
        if isinstance(d.get("occurred_at"), datetime):
            d["occurred_at"] = d["occurred_at"].isoformat()
    return {"items": docs}


@app.get("/api/positivity")
def positivity():
    import random
    return {
        "affirmation": random.choice(POSITIVE_AFFIRMATIONS),
        "quote": random.choice(QUOTES),
        "joke": random.choice(JOKES),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
