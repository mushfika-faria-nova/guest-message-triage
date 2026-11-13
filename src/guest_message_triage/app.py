from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="guest-message-triage")

class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    sender: str | None = None

class MessageOut(BaseModel):
    received: str
    length: int

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/messages")
def create_message(msg: MessageIn) -> MessageOut:
    return MessageOut(received=msg.text, length=len(msg.text))

