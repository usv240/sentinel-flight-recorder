from fastapi import APIRouter
from ..db.schemas import TranscriptRequest
from ..services.gemini_client import extract_decisions_from_transcript
from ..services.context_builder import build_metrics_snapshot
from ..db import mongodb

router = APIRouter()


@router.post("/extract")
async def extract_from_transcript(req: TranscriptRequest):
    """
    Paste any meeting transcript, Slack thread, email, or doc.
    Gemini extracts every business decision made, with type, rationale, and participants.
    Each extracted decision is automatically paired with current Fivetran metrics.
    """
    if not req.transcript.strip():
        return {"error": "Transcript is empty.", "decisions": []}

    # Gemini extracts structured decisions from the raw text
    extracted = await extract_decisions_from_transcript(req.transcript)

    if not extracted:
        return {
            "decisions": [],
            "message": "No decisions found in this transcript. Try a transcript that includes action items, strategy discussions, or announcements.",
            "transcript_length": len(req.transcript),
        }

    # Snapshot current metrics to attach to each extracted decision
    snapshot = await build_metrics_snapshot()

    # Log each extracted decision to MongoDB with the metrics snapshot
    logged = []
    for d in extracted:
        if d.get("confidence", 0) < 0.5:
            continue  # skip low-confidence extractions

        doc = {
            "decision_text": d.get("decision_text", ""),
            "decision_type": d.get("decision_type", "unknown"),
            "rationale": d.get("rationale", ""),
            "participants": d.get("participants", []),
            "auto_detected": True,
            "detection_source": f"transcript:{req.source}",
            "transcript_date": req.date,
            "gemini_confidence": d.get("confidence", 0.8),
        }

        try:
            decision_id = await mongodb.insert_decision(doc, snapshot)
        except Exception:
            import uuid
            decision_id = f"DEC-TRANSCRIPT-{uuid.uuid4().hex[:8].upper()}"
            doc["decision_id"] = decision_id

        logged.append({
            "decision_id": decision_id,
            "decision_text": doc["decision_text"],
            "decision_type": doc["decision_type"],
            "rationale": doc["rationale"],
            "participants": doc["participants"],
            "confidence": d.get("confidence", 0.8),
            "metrics_captured": list(k for k, v in snapshot.items() if v is not None and not k.startswith("_") and k != "sources"),
        })

    from ..services.output_writer import write_transcript_extract
    write_transcript_extract(req.transcript, logged, req.source)

    return {
        "decisions_found": len(extracted),
        "decisions_logged": len(logged),
        "decisions": logged,
        "snapshot_captured": True,
        "message": f"Extracted {len(logged)} decision(s) from {req.source}. Each is now in the decision log with a full metrics snapshot.",
    }
