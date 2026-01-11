from fastapi import FastAPI
from pydantic import BaseModel

# Creating FastApi application instance - main entry point of backend API to run the app
# FastAPI() - class provided by FASTAPI framework ,this object will listen for HTTP requests, route them to correct functions, validate IO, generates OpenAPI schema & generates swagger docs automatically
# app is just a variable, to store my application - Uvicorn expects - app.main:app, where app.main id a python file and app is variable inside that file.
# title and versions are metadata, appears in Swagger UI
app = FastAPI(title= "Chatbot basics API", version= "0.1.0")

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

def rule_based_reply(text: str) -> str:
    t =  text.strip().lower()

    if not t:
        return "Please type something and try again."

    greetings = {"hi", "hello", "hey", "good morning", "good evening"}
    if t in greetings:
        return "Hello! How can I help you today?"

    if "hours" in t or "open" in t:
        return "I can help with hours. What day are you asking about?"

    if "bye" in t or "goodbye" in t:
        return "Bye! Have a great day."

    return "Thanks! I’m a simple rule-based bot for now. Try saying 'hi' or ask about 'hours'."


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest): # req is a variable and ChatRequest is a Pydantic model
    reply = rule_based_reply(req.message) # req.message -> user's text I/P , reply - final chatbot text
    return ChatResponse(reply=reply)

