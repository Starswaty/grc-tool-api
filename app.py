from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import openai
import os
from dotenv import load_dotenv
import plotly.graph_objects as go
from typing import Dict, List, Optional

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="GRC Tool API")

# In-memory storage (replace with DB in production)
class Storage:
    def __init__(self):
        self.risks = []
        self.policies = {
            "Healthcare": "Outlines the company's commitment to employee health, medical coverage, and safety protocols.",
            "Data Privacy": "Ensures protection of user data, compliance with GDPR and internal data handling practices.",
            "IT Security": "Defines rules for protecting digital infrastructure, including access control and encryption.",
        }

storage = Storage()

@app.get("/")
async def root():
    return {"message": "GRC Tool API is running"}

# ---------- Policy Endpoints ----------

@app.get("/policies", response_model=Dict[str, str])
async def get_policies():
    """Get all policies"""
    return storage.policies

@app.post("/policies")
async def create_policy(
    category: str = Query(..., description="Policy category"),
    topic: str = Query(..., description="Policy topic"),
    notes: Optional[str] = Query(None, description="Optional additional notes")
):
    """Create a new policy using AI (via query params)"""
    final_category = category.strip()
    policy_explanation = f"Topic: {topic.strip()}."
    if notes and notes.strip():
        policy_explanation += f" Additional notes: {notes.strip()}"

    if not final_category or not topic.strip():
        raise HTTPException(status_code=400, detail="Category and topic are required")

    try:
        prompt = (
            f"You are a policy analyst with nine years of experience specializing in the '{final_category}' domain. "
            f"A user has provided the following explanation for a new company policy:\n\n"
            f"\"{policy_explanation}\"\n\n"
            f"Based on this, draft a comprehensive company policy structured as follows:\n"
            f"- Begin with 3 to 4 clear bullet points highlighting the key elements of the policy.\n"
            f"- Under each bullet point, provide a detailed description.\n"
            f"- Finally, include a comprehensive overview summarizing the entire policy.\n\n"
            f"The policy should include purpose, scope, responsibilities, and key requirements relevant to the domain and user explanation."
        )
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a GRC policy drafting expert."},
                {"role": "user", "content": prompt}
            ]
        )
        
        new_desc = response['choices'][0]['message']['content']
        storage.policies[final_category] = new_desc
        
        return {
            "message": f"Policy under '{final_category}' generated successfully",
            "policy": new_desc,
            "category": final_category
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating policy: {str(e)}")

# ---------- Risk Endpoints ----------

@app.get("/risks", response_model=List[dict])
async def get_risks():
    """Get all registered risks"""
    return storage.risks

@app.post("/risks")
async def create_risk(
    name: str = Query(...),
    domain: str = Query(...),
    likelihood: str = Query(...),
    description: str = Query(...)
):
    """Create a new risk using query parameters"""
    try:
        prompt = f"""
You are a senior enterprise risk analyst.

Risk Details:

* Name: {name}
* Domain: {domain}
* Likelihood: {likelihood}
* Description: {description}

Tasks:

1. Based on domain experience and likelihood, determine the **Impact Level** (High, Medium, or Low).
2. Then provide a structured mitigation plan including:

   * Short-Term Mitigation Plan
   * Long-Term Mitigation Strategy
   * Financial Impact (cost of mitigation vs. cost of ignoring)
   * Steps to Avoid This Risk in the Future
   * Consequences If This Risk Is Not Addressed
   * Relevant Stakeholders
   * Legal or Regulatory Considerations (if applicable)

Output must start with:
**Impact Level**: [High/Medium/Low]

Then provide the mitigation sections using markdown.
"""
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a GRC and enterprise risk management expert."},
                {"role": "user", "content": prompt}
            ]
        )

        risk_output = response['choices'][0]['message']['content']
        impact_line = next((line for line in risk_output.splitlines() if "Impact Level" in line), "")
        impact = impact_line.split(":")[-1].strip() if ":" in impact_line else "Unknown"

        new_risk = {
            "risk": name,
            "domain": domain,
            "likelihood": likelihood,
            "impact": impact,
            "description": description,
            "mitigation": risk_output
        }
        
        storage.risks.append(new_risk)
        
        return {
            "message": "Risk analysis generated successfully",
            "risk": new_risk
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing risk: {str(e)}")

# ---------- Mitigation via AI ----------

@app.post("/risks/mitigation")
async def get_risk_mitigation(
    risk_name: str = Query(...),
    impact: str = Query(...),
    likelihood: str = Query(...)
):
    """Get AI-generated mitigation for a specific risk via query params"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a GRC risk mitigation expert."},
                {"role": "user", "content": f"Suggest risk mitigation plan for a risk named '{risk_name}' with {impact} impact and {likelihood} likelihood."}
            ]
        )
        return {
            "risk": risk_name,
            "mitigation": response['choices'][0]['message']['content']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating mitigation: {str(e)}")

# ---------- GRC Chatbot ----------

@app.post("/chat")
async def chat_with_grc_bot(query: str = Query(...)):
    """Chat with the GRC AI assistant using query param"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant for GRC (Governance, Risk, Compliance)."},
                {"role": "user", "content": query}
            ]
        )
        return {
            "query": query,
            "response": response['choices'][0]['message']['content']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")
