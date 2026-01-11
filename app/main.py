from fastapi import FastAPI
from pydantic import BaseModel, Field
from uuid import uuid4
from threading import Lock
from typing import Dict,List,Literal,Optional

# Creating FastApi application instance - main entry point of backend API to run the app
# FastAPI() - class provided by FASTAPI framework ,this object will listen for HTTP requests, route them to correct functions, validate IO, generates OpenAPI schema & generates swagger docs automatically
# app is just a variable, to store my application - Uvicorn expects - app.main:app, where app.main id a python file and app is variable inside that file.
# title and versions are metadata, appears in Swagger UI
app = FastAPI(title= "Chatbot basics API", version= "0.2.0")


# -----------------------------
# Data models (API contracts)
# -----------------------------
class ChatRequest(BaseModel):
    """
    Request body model for POST /chat.

    - message: what the user typed
    - session_id: optional identifier to continue an existing conversation
      If the client doesn't send it, we generate a new one.
    """
    message: str = Field(..., description="User message text")
    session_id: Optional[str] = Field(
        default=None,
        description="Conversation/session id. Send this back to continue the chat.",
    )


class ChatMessage(BaseModel):
    """
    One message in the chat history.
    role is either 'user' or 'bot'
    """
    role: Literal["user", "bot"]
    content: str


class ChatResponse(BaseModel):
    """
    Response model for POST /chat.

    - session_id: always returned so the client can store and reuse it
    - reply: bot's response
    - history: full conversation history (for debugging / learning)
      In a real production app you might not return full history every time.
    """
    session_id: str
    reply: str
    history: List[ChatMessage]


# -----------------------------
# In-memory session storage
# -----------------------------
# sessions maps session_id -> list of ChatMessage
# This is "in-memory" meaning: if server restarts, memory resets.
sessions: Dict[str, List[ChatMessage]] = {}

# Lock ensures thread-safe updates when multiple requests happen at the same time.
sessions_lock = Lock()


# -----------------------------
# Chatbot logic (rule-based)
# -----------------------------
def rule_based_reply(text: str, history: List[ChatMessage]) -> str:
    """
    Decide bot reply using simple rules.
    Now that we have history, we can make it context-aware.

    `history` contains all previous messages in this session.
    """
    t = text.strip().lower()

    if not t:
        return "Please type something and try again."

    greetings = {"hi", "hello", "hey", "good morning", "good evening"}
    if t in greetings:
        # Example of using history: if user greeted before, respond differently
        user_greeting_count = sum(
            1 for msg in history if msg.role == "user" and msg.content.strip().lower() in greetings
        )
        if user_greeting_count >= 2:
            return "Hello again! 😊 What would you like to do next?"
        return "Hello! 😊 How can I help you today?"

    # Example: basic context memory: if the last bot message asked about a day
    # and user now types "monday", respond as if continuing the same topic.
    if history:
        last_bot = next((m for m in reversed(history) if m.role == "bot"), None)
        if last_bot and "what day are you asking about" in last_bot.content.lower():
            # treat the current user message as the day
            return f"Got it — you're asking about {text.strip()}. (We’ll add real hours later.)"

    if "hours" in t or "open" in t:
        return "I can help with hours. What day are you asking about?"

    if "bye" in t or "goodbye" in t:
        return "Bye! Have a great day."

    # Default response
    return "Thanks! I’m a simple stateful bot now. Try 'hi' or ask about 'hours'."


# -----------------------------
# API endpoints
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Main chat endpoint.

    1) Get or create session_id
    2) Append user message to session history
    3) Generate reply using rule_based_reply (history-aware)
    4) Append bot reply to history
    5) Return session_id + reply + full history
    """
    message = req.message.strip()

    # If caller doesn't pass session_id, we create a new one
    session_id = req.session_id or str(uuid4())

    with sessions_lock:
        history = sessions.get(session_id, [])

        # Add user message to history
        history.append(ChatMessage(role="user", content=message))

        # Create bot reply (can use history for context)
        reply = rule_based_reply(message, history)

        # Add bot reply to history
        history.append(ChatMessage(role="bot", content=reply))

        # Save back to sessions
        sessions[session_id] = history

    return ChatResponse(session_id=session_id, reply=reply, history=history)


@app.get("/sessions/{session_id}", response_model=List[ChatMessage])
def get_session(session_id: str):
    """
    Debug endpoint: fetch the full history for a session_id.
    """
    with sessions_lock:
        history = sessions.get(session_id)

    if history is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return history


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """
    Debug endpoint: delete a session (reset conversation).
    """
    with sessions_lock:
        existed = session_id in sessions
        if existed:
            del sessions[session_id]

    return {"deleted": existed, "session_id": session_id}
