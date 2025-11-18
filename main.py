# app/main.py
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional
import math

app = FastAPI(title="Sherpa Scout - Scouting AI Endpoint")

# ---------- Input models ----------
class Stat(BaseModel):
    name: str
    value: float

class Player(BaseModel):
    full_name: str
    position: str
    age: int
    stats: List[Stat] = []
    marketability_score: Optional[float] = Field(0.5, ge=0.0, le=1.0)
    highlights: Optional[List[str]] = []

# ---------- Internal helpers (simple deterministic logic) ----------
def compute_overall_score(stats: List[Stat]) -> float:
    if not stats:
        return 50.0
    # average normalized stat -> 0..100
    vals = [s.value for s in stats]
    mean = sum(vals)/len(vals)
    # simple normalization: assume typical stat values cluster; clamp values
    score = max(0.0, min(100.0, mean))
    return score

def compute_fit_scores(player: Player) -> dict:
    overall = compute_overall_score(player.stats)
    # team fit: prefers younger players for development, position coherence, and moderate marketability
    age_factor = max(0, (30 - player.age)) / 30  # 0..1 (younger higher)
    position_factor = 1.0 if player.position.lower() in ("guard","forward","center","midfielder","forward") else 0.8
    market = player.marketability_score
    team_fit = (overall/100)*0.6 + age_factor*0.2 + market*0.2
    agency_fit = market*0.6 + (overall/100)*0.4
    opportunity = (team_fit + agency_fit) / 2
    return {
        "overall_score": round(overall,2),
        "team_fit": round(team_fit*100,2),
        "agency_fit": round(agency_fit*100,2),
        "opportunity_score": round(opportunity*100,2)
    }

def draft_projection(player: Player, overall_score: float) -> dict:
    # very simple heuristic:
    if overall_score >= 85:
        round_ = 1
        pick_est = max(1, int(30 - (overall_score-85)))  # top picks
        prob = 0.95
    elif overall_score >= 70:
        round_ = 1
        pick_est = int(30 + (85 - overall_score))
        prob = 0.75
    elif overall_score >= 55:
        round_ = 2
        pick_est = int(50 + (70 - overall_score))
        prob = 0.45
    else:
        round_ = 3
        pick_est = None
        prob = 0.12
    return {"projected_round": round_, "projected_pick_estimate": pick_est, "draft_probability": round(prob,2)}

def nil_value_estimate(player: Player, overall_score: float) -> dict:
    # simple monetary heuristic in USD
    base = (overall_score / 100) * 200_000  # base annual NIL
    brand_multiplier = 1 + player.marketability_score  # 1..2
    projection_12m = base * brand_multiplier * 1.1
    suggestions = []
    if player.marketability_score > 0.8:
        suggestions.append("National brand endorsements; social-first campaigns")
    elif player.marketability_score > 0.5:
        suggestions.append("Regional brands, niche sponsors")
    else:
        suggestions.append("Local sponsorships, community partnerships")
    return {"current_estimated_nil": int(base), "projected_12m_nil": int(projection_12m), "brand_suggestions": suggestions}

def build_pitch(player: Player, fit: dict) -> str:
    pitch = f"""Pitch for {player.full_name} ({player.position}, age {player.age})
Overall Score: {fit['overall_score']}
Team Fit: {fit['team_fit']} | Agency Fit: {fit['agency_fit']}
Opportunity: {fit['opportunity_score']}

Why sign:
- Plays {player.position} with consistent metrics.
- Marketability: {player.marketability_score}
- Key strengths: {"; ".join(player.highlights) if player.highlights else 'N/A'}

Recommended next steps:
1. Shortlist for targeted tryout.
2. Produce highlight reel and social push.
3. Introduce to 2-3 regional brands for initial NIL deals.
"""
    return pitch

# ---------- API endpoints ----------
class ReportResponse(BaseModel):
    player: Player
    fit_scores: dict
    draft_projection: dict
    nil_estimate: dict
    report: str

@app.post("/generate_report", response_model=ReportResponse)
def generate_report(player: Player):
    fit = compute_fit_scores(player)
    draft = draft_projection(player, fit["overall_score"])
    nil_est = nil_value_estimate(player, fit["overall_score"])
    pitch = build_pitch(player, fit)
    return {
        "player": player,
        "fit_scores": fit,
        "draft_projection": draft,
        "nil_estimate": nil_est,
        "report": pitch
    }

@app.get("/health")
def health():
    return {"status": "ok"}
