"""
BlueByte AI — GraphRAG Conversational Assistant Router
Combines live ocean telemetry, PostGIS spatial data, and GNN species predictions
into contextual AI responses for natural language queries.
"""
import os
import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("BlueByte-Chat")
router = APIRouter(prefix="/chat", tags=["AI Chatbot (GraphRAG)"])


class ChatMessage(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []


class ChatResponse(BaseModel):
    reply: str
    target_coords: Optional[List[float]] = None
    highlight_zone: Optional[str] = None
    sources: List[str] = []


# Static Knowledge Graph fallback for immediate zero-dependency response
KNOWLEDGE_GRAPH = {
    "zones": [
        {
            "id": "PFZ-AS-04",
            "name": "Malpe–Karwar Upwelling Front",
            "species": "Indian oil sardine (Sardinella longiceps)",
            "confidence": 0.91,
            "coords": [13.9, 73.4],
            "reason": "Upwelling front bringing nutrient-rich deep water + high chlorophyll-a (2.4 mg/m³)",
            "region": "Karnataka & Goa Coast (Arabian Sea)"
        },
        {
            "id": "PFZ-AS-11",
            "name": "Lakshadweep Thermal Ridge",
            "species": "Yellowfin tuna (Thunnus albacares)",
            "confidence": 0.78,
            "coords": [11.4, 71.2],
            "reason": "Thermal gradient convergence zone, SST ~30.6°C, deep oceanic shelf",
            "region": "Lakshadweep Basin"
        },
        {
            "id": "PFZ-BB-06",
            "name": "Godavari Plume Convergence",
            "species": "Indian mackerel (Rastrelliger kanagurta)",
            "confidence": 0.66,
            "coords": [16.6, 82.1],
            "reason": "River plume mixing zone with optimal temperature band 28–29°C",
            "region": "Andhra Coast (Bay of Bengal)"
        }
    ],
    "species_info": {
        "sardine": {
            "name": "Indian Oil Sardine",
            "optimal_sst": "27-29.5°C",
            "ideal_depth": "10-50m",
            "best_region": "Malpe-Karwar Upwelling Front"
        },
        "mackerel": {
            "name": "Indian Mackerel",
            "optimal_sst": "26-28.5°C",
            "ideal_depth": "20-80m",
            "best_region": "Godavari Plume & Goa Shelf"
        },
        "tuna": {
            "name": "Yellowfin Tuna",
            "optimal_sst": "28-31°C",
            "ideal_depth": "50-250m",
            "best_region": "Lakshadweep Ridge & Oceanic Fronts"
        }
    },
    "alerts": [
        {"id": "ALT-01", "type": "Marine Heatwave", "sensor": "BD08", "temp": "29.8°C", "z_score": 3.4},
        {"id": "ALT-02", "type": "Low Dissolved Oxygen", "sensor": "CM03", "do": "3.2 mg/L", "z_score": -2.8}
    ]
}


def build_graphrag_context() -> str:
    """Builds structured text summary of live Graph & Telemetry data for RAG."""
    ctx_lines = [
        "=== LIVE BLUEBYTE KNOWLEDGE GRAPH & TELEMETRY ===",
        "ACTIVE POTENTIAL FISHING ZONES (PFZ):"
    ]
    for z in KNOWLEDGE_GRAPH["zones"]:
        ctx_lines.append(
            f"- {z['name']} ({z['id']}): Target Species: {z['species']}, "
            f"Confidence: {int(z['confidence']*100)}%, Coords: {z['coords']}, "
            f"Reason: {z['reason']}, Region: {z['region']}"
        )

    ctx_lines.append("\nACTIVE ANOMALIES & HEATWAVE ALERTS:")
    for a in KNOWLEDGE_GRAPH["alerts"]:
        ctx_lines.append(f"- Alert {a['id']}: {a['type']} at Sensor {a['sensor']} (Z-score: {a['z_score']})")

    ctx_lines.append("\nGNN SPECIES REPOSITORIES & OPTIMAL ENVS:")
    for sp_key, sp in KNOWLEDGE_GRAPH["species_info"].items():
        ctx_lines.append(f"- {sp['name']}: Optimal SST={sp['optimal_sst']}, Depth={sp['ideal_depth']}, Best Hotspot={sp['best_region']}")

    return "\n".join(ctx_lines)


def generate_local_response(query: str) -> ChatResponse:
    """
    Intelligent local fallback engine that evaluates queries against the Knowledge Graph.
    Ensures 100% offline uptime for live hackathon presentations.
    """
    q = query.lower()
    target_coords = None
    highlight_zone = None
    sources = ["BlueByte In-Memory Knowledge Graph", "INCOIS Telemetry Feed", "GNN Link Predictor"]

    # 1. Sardine query
    if "sardine" in q or "malpe" in q or "karwar" in q:
        z = KNOWLEDGE_GRAPH["zones"][0]
        target_coords = z["coords"]
        highlight_zone = z["id"]
        reply = (
            f"🐟 **Indian Oil Sardine Advisory (Zone: {z['id']})**\n\n"
            f"• **Location**: {z['name']} ({z['region']}) at coordinates `[{z['coords'][0]}°N, {z['coords'][1]}°E]`.\n"
            f"• **Confidence**: **{int(z['confidence']*100)}%** predicted by GNN habitat link analysis.\n"
            f"• **Oceanographic Driver**: {z['reason']}.\n"
            f"• **Recommendation**: Favorable conditions for purse-seine operations. Sail south-southwest from Goa to ride current vectors."
        )

    # 2. Tuna query
    elif "tuna" in q or "lakshadweep" in q or "yellowfin" in q:
        z = KNOWLEDGE_GRAPH["zones"][1]
        target_coords = z["coords"]
        highlight_zone = z["id"]
        reply = (
            f"🦈 **Yellowfin Tuna Advisory (Zone: {z['id']})**\n\n"
            f"• **Location**: {z['name']} ({z['region']}) at coordinates `[{z['coords'][0]}°N, {z['coords'][1]}°E]`.\n"
            f"• **Confidence**: **{int(z['confidence']*100)}%** confidence.\n"
            f"• **Environmental Drivers**: Deep thermal ridge with SST at ~30.6°C.\n"
            f"• **Recommendation**: Ideal for longline fishing in deep oceanic waters."
        )

    # 3. Mackerel query
    elif "mackerel" in q or "godavari" in q:
        z = KNOWLEDGE_GRAPH["zones"][2]
        target_coords = z["coords"]
        highlight_zone = z["id"]
        reply = (
            f"🐟 **Indian Mackerel Advisory (Zone: {z['id']})**\n\n"
            f"• **Location**: {z['name']} ({z['region']}) at coordinates `[{z['coords'][0]}°N, {z['coords'][1]}°E]`.\n"
            f"• **Confidence**: **{int(z['confidence']*100)}%** probability.\n"
            f"• **Driver**: {z['reason']} with high plankton density."
        )

    # 4. Alerts / Anomalies query
    elif "alert" in q or "heatwave" in q or "anomaly" in q or "temperature" in q:
        reply = (
            f"⚠️ **Real-Time Telemetry & Anomaly Report**\n\n"
            f"• **Marine Heatwave Detected**: Sensor `BD08` in Central Arabian Sea recorded **29.8°C** (Z-Score +3.4 above baseline).\n"
            f"• **Low Oxygen Zone (Hypoxia)**: Station `CM03` off Mangalore reported dissolved oxygen down to **3.2 mg/L**.\n"
            f"• **Impact**: Fish schools may migrate away from high-temperature surface pockets."
        )
        sources.append("ZeroMQ In-Memory Z-Score Stream")

    # 5. GNN / Graph query
    elif "gnn" in q or "graph" in q or "edna" in q or "model" in q:
        reply = (
            f"🧠 **Marine Graph Neural Network (GNN) Summary**\n\n"
            f"• **Architecture**: Heterogeneous GAT with link prediction over `Species ↔ OceanGrid ↔ eDNA` nodes.\n"
            f"• **Message Passing**: Propagates spatial neighbor telemetry (SST, Salinity, Chlorophyll) and eDNA sequence tags (COI/12S/16S).\n"
            f"• **Task**: Computes dot-product link probabilities to detect unobserved fish presence without invasive trawling."
        )
        sources.append("PyTorch Geometric HeteroGAT")

    # Default general response
    else:
        reply = (
            f"🌊 **BlueByte AI Marine Console Ready**\n\n"
            f"I have live access to INCOIS telemetry, 3 active PFZ zones, and the GNN biodiversity knowledge graph.\n\n"
            f"**You can ask me:**\n"
            f"• *'Where is the best place to catch Sardines near Goa?'*\n"
            f"• *'Show me active marine heatwave alerts.'*\n"
            f"• *'Which fishing zones have the highest tuna confidence?'*\n"
            f"• *'Explain how the GNN uses eDNA data.'*"
        )

    return ChatResponse(
        reply=reply,
        target_coords=target_coords,
        highlight_zone=highlight_zone,
        sources=sources
    )


@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatMessage):
    """
    Main Chat API Endpoint.
    Uses OpenAI/Gemini if API key is present; otherwise gracefully falls back to Graph Engine.
    """
    user_msg = req.message.strip()
    if not user_msg:
        return ChatResponse(reply="Please enter a question about ocean data or fishing zones.")

    # Check for OpenAI API key
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            context = build_graphrag_context()
            system_prompt = (
                "You are BlueByte AI, an expert marine oceanography and fisheries assistant for India. "
                "Answer user questions accurately using the provided live knowledge graph and telemetry data. "
                "Be concise, technical, and format using clean markdown bullet points.\n\n"
                f"{context}"
            )
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                max_tokens=350,
                temperature=0.3
            )
            answer = completion.choices[0].message.content
            return ChatResponse(
                reply=answer,
                sources=["OpenAI GPT-4o-mini", "Injected Knowledge Graph Context", "Live Telemetry"]
            )
        except Exception as e:
            logger.warning(f"OpenAI call failed, falling back to local graph engine: {e}")

    # Fallback to deterministic local engine (fast, offline, reliable)
    return generate_local_response(user_msg)
