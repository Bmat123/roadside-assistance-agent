"""
FastAPI server for Roadside Assistance Agent
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Optional, List
import uvicorn
import json

from config import API_HOST, API_PORT, CORS_ORIGINS, STATIC_DIR
from services.agent import RoadsideAgent

app = FastAPI(title="Roadside Assistance API")
agent = RoadsideAgent()

# --- CORS MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SERVE STATIC FILES ---
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# --- DATA MODELS ---
class UserInput(BaseModel):
    session_id: str
    text: str

class AgentResponse(BaseModel):
    voice_response: str
    ui_update: Optional[Dict] = None
    collected_data: Optional[Dict] = None
    is_covered: Optional[bool] = None
    dispatch_details: Optional[Dict] = None
    conversation_complete: Optional[bool] = False

# --- STATE MANAGEMENT (In-Memory) ---
sessions: Dict[str, List[Dict]] = {}

def get_history(session_id: str) -> List[Dict]:
    """Get or create conversation history for a session"""
    if session_id not in sessions:
        sessions[session_id] = []
    return sessions[session_id]

# --- API ENDPOINTS ---
@app.get("/")
async def root():
    """Redirect to the frontend"""
    return {"message": "Roadside Assistance API", "frontend": "/static/index.html"}

@app.post("/agent/chat", response_model=AgentResponse)
async def chat(input_data: UserInput):
    """Main chat endpoint for AI agent interaction"""
    history = get_history(input_data.session_id)
    user_text = input_data.text

    # Get response from AI Agent
    ai_response = agent.process_request(history, user_text)

    # Update conversation history
    history.append({"role": "user", "parts": [user_text]})
    history.append({"role": "model", "parts": [json.dumps(ai_response)]})

    # Return structured response
    return AgentResponse(
        voice_response=ai_response.get("voice_response", "I am sorry, I didn't catch that."),
        ui_update=ai_response.get("ui_update"),
        collected_data=ai_response.get("collected_data"),
        is_covered=ai_response.get("is_covered"),
        dispatch_details=ai_response.get("dispatch_details"),
        conversation_complete=ai_response.get("conversation_complete", False)
    )

# --- SERVER STARTUP ---
if __name__ == "__main__":
    print("🚀 Starting Roadside Assistance AI Agent Backend...")
    print(f"📍 Backend running at: http://{API_HOST}:{API_PORT}")
    print(f"📖 API docs available at: http://{API_HOST}:{API_PORT}/docs")
    print(f"🌐 Frontend available at: http://{API_HOST}:{API_PORT}/static/index.html")
    print("\n✅ Press Ctrl+C to stop the server\n")

    uvicorn.run(app, host=API_HOST, port=API_PORT)
