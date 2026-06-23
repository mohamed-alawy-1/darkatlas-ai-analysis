import json
from datetime import datetime, timezone
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from app.core.config import settings


def _get_llm():
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        api_key=settings.anthropic_api_key,
        base_url=settings.anthropic_base_url,
        max_tokens=2048,
    )


def _assets_to_text(assets: list[dict]) -> str:
    return json.dumps(assets, default=str, ensure_ascii=False, indent=2)


async def natural_language_query(assets: list[dict], query: str) -> dict:
    llm = _get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an asset query engine for a security platform.
You receive a list of assets in JSON and a natural-language query.
Your job is to return ONLY the assets from the provided list that match the query.
NEVER invent or hallucinate assets. If no assets match, return an empty list.
Return valid JSON: {{"matched": [...list of matching asset objects...], "explanation": "why these matched"}}"""),
        ("human", "Assets:\n{assets}\n\nQuery: {query}"),
    ])

    chain = prompt | llm | JsonOutputParser()
    try:
        result = await chain.ainvoke({"assets": _assets_to_text(assets), "query": query})
        return result
    except Exception as exc:
        return {"matched": [], "explanation": f"Query failed: {exc}"}


async def risk_score(assets: list[dict], asset_id: str | None = None) -> dict:
    llm = _get_llm()

    target = assets
    if asset_id:
        target = [a for a in assets if a["id"] == asset_id]
        if not target:
            return {"error": f"Asset {asset_id} not found"}

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a security risk analyst for an Attack Surface Monitoring platform.
Analyze the provided assets and return a risk assessment.
Focus on: expired/expiring certificates, exposed sensitive services (SSH, RDP, DB ports),
end-of-life technologies, stale assets still marked active.
Return valid JSON:
{{
  "overall_risk": "low|medium|high|critical",
  "score": <0-100>,
  "findings": [{{"asset_id": "...", "asset_value": "...", "risk": "...", "reason": "..."}}],
  "summary": "concise paragraph summary"
}}
Base score and findings ONLY on the provided asset data. Do not invent findings."""),
        ("human", "Assets to analyze:\n{assets}"),
    ])

    chain = prompt | llm | JsonOutputParser()
    try:
        result = await chain.ainvoke({"assets": _assets_to_text(target)})
        return result
    except Exception as exc:
        return {"error": f"Risk scoring failed: {exc}", "score": 0}


async def enrich_asset(asset: dict) -> dict:
    llm = _get_llm()

    now = datetime.now(timezone.utc).isoformat()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an asset classification engine for a security platform.
Given a single asset, classify and enrich it.
Classification rules:
- env_category: "prod" if value/tags suggest production (no dev/staging/test prefix), "staging" if staging/uat/qa prefix, "dev" if dev/local/test prefix, "unknown" otherwise
- category: what kind of asset it is (e.g. "web-frontend", "api-endpoint", "database", "cdn", "mail", "vpn", "storage", "monitoring")
- criticality: "critical" if prod + (cert/service/ip), "high" if prod + subdomain/domain, "medium" if staging, "low" if dev/stale

Return valid JSON only:
{{
  "env_category": "prod|staging|dev|unknown",
  "category": "<category string>",
  "criticality": "critical|high|medium|low",
  "enriched_metadata": {{...any additional inferred fields...}},
  "reasoning": "brief explanation"
}}

Current UTC time: {now}
Base ALL classifications on the asset data provided. Do not invent information."""),
        ("human", "Asset to classify:\n{asset}"),
    ])

    chain = prompt | llm | JsonOutputParser()
    try:
        result = await chain.ainvoke({"asset": json.dumps(asset, default=str), "now": now})
        return result
    except Exception as exc:
        return {"error": f"Enrichment failed: {exc}"}


async def generate_report(assets: list[dict], filters: dict | None = None) -> dict:
    llm = _get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a security analyst writing an asset inventory and risk report for a CISO.
Write a clear, concise, professional report based ONLY on the provided asset data.
Structure:
1. Executive Summary (2-3 sentences)
2. Asset Inventory Overview (counts by type and status)
3. Key Risk Findings (expired certs, exposed services, stale assets, etc.)
4. Recommendations (top 3-5 actionable items)

Rules:
- Only reference assets in the provided data
- Be specific: name actual values, dates, counts
- Do not invent or assume anything not in the data
Return JSON: {{"report": "<full markdown report text>", "asset_count": <n>, "risk_level": "low|medium|high|critical"}}"""),
        ("human", "Asset dataset ({count} assets):\n{assets}"),
    ])

    chain = prompt | llm | JsonOutputParser()
    try:
        result = await chain.ainvoke({
            "assets": _assets_to_text(assets),
            "count": len(assets),
        })
        return result
    except Exception as exc:
        return {"error": f"Report generation failed: {exc}", "report": ""}
