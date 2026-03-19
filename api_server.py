from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import json

from engine.runtime import AgentRuntime
from agents.outbound_recommendation import OutboundRecommendationAgent
from engine.campaign_loader import load_campaigns
from engine.session_store import sessions

app = FastAPI()

@app.get("/dashboard")
def dashboard():
    return FileResponse("static/index.html")

# ── CORS: allow the dashboard HTML to call /make-call ──────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your dashboard domain in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load campaigns once at startup ─────────────────────────────────────────
campaigns = load_campaigns("campaigns.xlsx")

# ── Exotel credentials (set these in your .env / VPS environment) ──────────
EXOTEL_SID    = os.getenv("EXOTEL_SID")
EXOTEL_KEY    = os.getenv("EXOTEL_KEY")
EXOTEL_TOKEN  = os.getenv("EXOTEL_TOKEN")
EXOTEL_CALLER = os.getenv("EXOTEL_CALLER_ID")   # your ExoPhone virtual number
EXOTEL_REGION = os.getenv("EXOTEL_REGION", "@api.in.exotel.com")

# Your public VPS domain — Exotel will POST speech here
BASE_URL = os.getenv("BASE_URL", "https://api.agentix.nsdaindia.com")


# ───────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ───────────────────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    return {"status": "agent server running", "campaigns_loaded": len(campaigns)}


# ───────────────────────────────────────────────────────────────────────────
# /make-call  ← called by the dashboard (one click per row)
#
# Flow:
#   Dashboard clicks "Call" → POST /make-call
#   → we hit Exotel API "Connect number to call flow"
#   → Exotel dials customer's phone (campaign["phone"])
#   → customer picks up → Exotel hits GET /voice?CallSid=xxx&campaign_index=N
#   → /voice creates a runtime for that campaign and returns TwiML
# ───────────────────────────────────────────────────────────────────────────

class MakeCallRequest(BaseModel):
    campaign_index: int          # which row from campaigns.xlsx (0-based)


@app.post("/make-call")
async def make_call(req: MakeCallRequest):

    print("MAKE_CALL_HIT", flush=True)
    print(f"BASE_URL={BASE_URL}", flush=True)
    print(f"EXOTEL_SID={EXOTEL_SID}", flush=True)
    # Validate credentials are configured
    if not all([EXOTEL_SID, EXOTEL_KEY, EXOTEL_TOKEN, EXOTEL_CALLER]):
        raise HTTPException(
            status_code=500,
            detail="Exotel credentials not configured. Set EXOTEL_SID, EXOTEL_KEY, EXOTEL_TOKEN, EXOTEL_CALLER_ID env vars."
        )

    if req.campaign_index < 0 or req.campaign_index >= len(campaigns):
        raise HTTPException(status_code=400, detail=f"campaign_index out of range (0–{len(campaigns)-1})")

    campaign = campaigns[req.campaign_index]
    to_number = campaign["phone"]

    # The voice webhook URL — we pass campaign_index so /voice knows which campaign
    voice_url = f"http://my.exotel.com/{EXOTEL_SID}/exoml/start_voice/1205768"

    exotel_url = (
        f"https://{EXOTEL_KEY}:{EXOTEL_TOKEN}{EXOTEL_REGION}"
        f"/v1/Accounts/{EXOTEL_SID}/Calls/connect.json"
    )

    payload = {
        "To": to_number,
        "From": EXOTEL_CALLER,
        "CallerId": EXOTEL_CALLER,
        "CallType": "trans",
        "TimeOut": "30",
        "Url": f"http://my.exotel.com/{EXOTEL_SID}/exoml/start_voice/1205768",
        "StatusCallback": f"{BASE_URL}/call-status",
        "CustomField": str(req.campaign_index),
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(exotel_url, data=payload)

        print(f"Exotel response: {r.status_code}")
        print(f"Exotel body: {r.text}")
        print(f"Url sent: {BASE_URL}/voice")

        if r.status_code != 200:
            raise HTTPException(
                status_code=r.status_code,
                detail=f"Exotel error: {r.text}"
            )

        data = r.json()
        call_sid = data.get("Call", {}).get("Sid")

        return {
            "ok": True,
            "call_sid": call_sid,
            "to": to_number,
            "campaign": campaign["organization_name"],
            "offer": campaign["offer_title"],
        }

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Exotel: {e}")

    import base64
    auth = base64.b64encode(f"{EXOTEL_KEY}:{EXOTEL_TOKEN}".encode()).decode()
    print(f"SID: {EXOTEL_SID}")
    print(f"KEY: {EXOTEL_KEY}")
    print(f"TOKEN: {EXOTEL_TOKEN}")
    print(f"CALLER: {EXOTEL_CALLER}")
    print(f"REGION: {EXOTEL_REGION}")
    print(f"Full URL: https://{EXOTEL_KEY}:{EXOTEL_TOKEN}{EXOTEL_REGION}/v1/Accounts/{EXOTEL_SID}/Calls/connect.json")


# ───────────────────────────────────────────────────────────────────────────
# /voice  ← Exotel fetches this every turn of the conversation
#
# First hit (no CallSid in sessions):  create runtime, return opening line
# Subsequent hits:                      feed speech, return next agent line
# ───────────────────────────────────────────────────────────────────────────

@app.api_route("/voice", methods=["GET", "POST"])
async def voice_webhook(request: Request):
    # Exotel sends params as query string or form-data — handle both
    params = dict(request.query_params)
    try:
        form = await request.form()
        params.update(form)
    except Exception:
        pass


    call_type = params.get("CallType", "")
    if call_type == "call-attempt":
        return Response(
            f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
      <Redirect>{BASE_URL}/voice</Redirect>
    </Response>""",
            media_type="application/xml"
        )

    call_sid = params.get("CallSid", "default_session")
    speech   = params.get("SpeechResult", "")

    # ── First turn: create a new runtime for this call ──
    if call_sid not in sessions:
        # campaign_index passed in URL when we initiated the call
        try:
            campaign_index = int(params.get("CustomField", 0))
            campaign = campaigns[campaign_index]
        except (ValueError, IndexError):
            campaign = campaigns[0]

        agent   = OutboundRecommendationAgent()
        runtime = AgentRuntime(agent=agent, campaign_context=campaign)
        sessions[call_sid] = runtime

        # Empty string → triggers the OPEN state prompt
        response_text = runtime.process_turn("")

    # ── Subsequent turns: feed speech result ──
    else:
        runtime       = sessions[call_sid]
        response_text = runtime.process_turn(speech)

    # ── Build Exotel TwiML ──
    # If agent returned None or empty (e.g. END state), close gracefully
    if not response_text or response_text.strip() == "":
        response_text = "Thank you for your time. Have a great day."

    # Detect if conversation is over — don't Gather, just Say and hang up
    is_terminal = (runtime.state_id == "END")

    if is_terminal:
        # Clean up session memory
        sessions.pop(call_sid, None)
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="female">{_escape_xml(response_text)}</Say>
</Response>"""
    else:
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="female">{_escape_xml(response_text)}</Say>
  <Gather input="speech"
          action="{BASE_URL}/voice?campaign_index={params.get('campaign_index', 0)}"
          method="POST"
          timeout="5"
          speechTimeout="2"
          finishOnKey="#">
  </Gather>
  <Redirect method="POST">{BASE_URL}/voice?campaign_index={params.get('campaign_index', 0)}&amp;CallSid={call_sid}</Redirect>
</Response>"""

    return Response(xml, media_type="application/xml")


# ───────────────────────────────────────────────────────────────────────────
# /call-status  ← Exotel POSTs here when the call ends
# ───────────────────────────────────────────────────────────────────────────

@app.post("/call-status")
async def call_status(request: Request):
    try:
        data = await request.json()
    except Exception:
        form = await request.form()
        data = dict(form)

    call_sid   = data.get("CallSid")
    status     = data.get("Status")       # completed / failed / busy / no-answer
    duration   = data.get("ConversationDuration")
    rec_url    = data.get("RecordingUrl")
    campaign_i = data.get("CustomField")  # the index we passed when initiating

    print(f"[CallStatus] SID={call_sid} Status={status} Duration={duration}s Campaign={campaign_i}")

    # Clean up any lingering session
    if call_sid and call_sid in sessions:
        sessions.pop(call_sid)

    # → Add your DB logging / webhook / CRM update here

    return {"ok": True}


# ───────────────────────────────────────────────────────────────────────────
# /campaigns  ← dashboard can fetch this to populate the table
# ───────────────────────────────────────────────────────────────────────────

@app.get("/campaigns")
def get_campaigns():
    return [
        {
            "index": i,
            "organization_name": c["organization_name"],
            "phone": c["phone"],
            "service_name": c["service_name"],
            "offer_title": c["offer_title"],
            "location": c["location"],
            "domain": c["domain"],
        }
        for i, c in enumerate(campaigns)
    ]


# ───────────────────────────────────────────────────────────────────────────
# HELPERS
# ───────────────────────────────────────────────────────────────────────────

def _escape_xml(text: str) -> str:
    """Prevent agent text from breaking TwiML."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
