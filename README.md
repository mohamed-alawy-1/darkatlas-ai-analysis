# DarkAtlas AI - Asset Analysis API

LangChain-powered asset analysis for the DarkAtlas Attack Surface Monitoring platform.

## Stack

- **Python 3.12** + **FastAPI** + **SQLAlchemy 2 (async)** + **PostgreSQL 16**
- **LangChain** + **Claude (Anthropic)** for all analysis capabilities
- **uv** for dependency management
- **Docker Compose** for one-command deployment

---

## Quick Start

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
docker compose up --build
```

- API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`

### Import the sample dataset

```bash
curl -X POST http://localhost:8000/api/v1/import \
  -H "Content-Type: application/json" \
  -d "{\"assets\": $(cat data/sample_assets.json)}"
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | - | Claude API key (required for analysis) |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@db:5432/darkatlas_ai` | PostgreSQL connection URL |
| `POSTGRES_DB` | `darkatlas_ai` | Database name |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `postgres` | Database password |

---

## API Reference

### Import Assets

```
POST /api/v1/import
```

Body: `{"assets": [...]}`

Response: `{"imported": 13, "updated": 0, "errors": []}`

Re-importing the same dataset is fully idempotent - returns `{"imported": 0, "updated": 13, "errors": []}`.

### List Assets

```
GET /api/v1/assets?type=certificate&status=active&tag=prod
```

### Get Single Asset

```
GET /api/v1/assets/{asset_id}
```

### Analyze - Single Endpoint, Four Modes

```
POST /api/v1/analyze
```

Body:
```json
{
  "mode": "query|risk|enrich|report",
  "query": "...",
  "asset_id": "...",
  "filters": {"type": "...", "status": "..."}
}
```

---

## Analysis Capabilities

### 1. Natural-Language Query (`mode=query`)

Translate a plain English question into a filtered asset list. The model only returns assets from the actual database - no hallucination.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"mode": "query", "query": "show me all expired certificates"}'
```

**Response:**
```json
{
  "matched": [
    {
      "id": "a10",
      "type": "certificate",
      "value": "CN=api.example.com",
      "metadata": {"issuer": "Let's Encrypt", "expires": "2025-01-02T00:00:00Z"}
    }
  ],
  "explanation": "Certificate CN=api.example.com expired on 2025-01-02, which is in the past."
}
```

**More example queries:**
- `"show me all prod subdomains"`
- `"which services are exposing SSH?"`
- `"find technologies that are end of life"`
- `"show me all stale assets"`

---

### 2. Risk Scoring & Summarization (`mode=risk`)

Produce a risk score (0-100) and findings for an asset or group.

**Request - single asset:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"mode": "risk", "asset_id": "a10"}'
```

**Request - filtered group:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"mode": "risk", "filters": {"status": "active"}}'
```

**Response:**
```json
{
  "overall_risk": "high",
  "score": 78,
  "findings": [
    {
      "asset_id": "a10",
      "asset_value": "CN=api.example.com",
      "risk": "Expired certificate",
      "reason": "Certificate expired 2025-01-02, over a year ago. Production API is running with an expired cert."
    },
    {
      "asset_id": "a9",
      "asset_value": "203.0.113.10:3306",
      "risk": "Exposed database port",
      "reason": "MySQL port 3306 is internet-facing on a production IP."
    },
    {
      "asset_id": "a14",
      "asset_value": "mysql",
      "risk": "End-of-life technology",
      "reason": "MySQL 5.7 reached EOL on 2023-10-31."
    }
  ],
  "summary": "The asset inventory shows critical risks: an expired TLS certificate on the production API, an internet-facing MySQL database, and an end-of-life MySQL version. Immediate remediation is required."
}
```

---

### 3. Enrichment & Categorization (`mode=enrich`)

Classify an asset and enrich its metadata. Updates the database automatically.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"mode": "enrich", "asset_id": "a2"}'
```

**Response:**
```json
{
  "env_category": "prod",
  "category": "api-endpoint",
  "criticality": "high",
  "enriched_metadata": {
    "inferred_purpose": "REST API endpoint",
    "exposure": "public"
  },
  "reasoning": "Value 'api.example.com' and tag 'prod' indicate a production API endpoint. Subdomains on production are high criticality."
}
```

---

### 4. Report Generation (`mode=report`)

Generate a readable markdown inventory and risk report.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"mode": "report"}'
```

**With filters:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"mode": "report", "filters": {"status": "active"}}'
```

**Response:**
```json
{
  "risk_level": "high",
  "asset_count": 15,
  "report": "# Asset Inventory & Risk Report\n\n## Executive Summary\nThe organization currently tracks 15 internet-facing assets across 6 categories. Critical findings include an expired TLS certificate on the production API, an exposed MySQL database port, and an end-of-life MySQL 5.7 installation.\n\n## Asset Inventory Overview\n- Domains: 1 (1 active)\n- Subdomains: 3 (2 active, 1 stale)\n- IP Addresses: 2 (2 active)\n- Services: 3 (3 active)\n- Certificates: 3 (3 active, 1 expired)\n- Technologies: 3 (3 active)\n\n## Key Risk Findings\n1. **Expired Certificate** - CN=api.example.com expired 2025-01-02\n2. **Exposed Database** - MySQL on 203.0.113.10:3306 is internet-facing\n3. **End-of-Life Technology** - MySQL 5.7 EOL since 2023-10-31\n4. **SSH Exposure** - Port 22 open on production IP 93.184.216.34\n\n## Recommendations\n1. Renew the TLS certificate for api.example.com immediately\n2. Firewall MySQL port 3306 - restrict to internal network only\n3. Upgrade MySQL 5.7 to 8.x\n4. Review SSH access policy on 93.184.216.34\n5. Investigate stale subdomain dev.example.com"
}
```

---

## Design Decisions

**Single `/analyze` endpoint with `mode`** - keeps the API surface minimal as required by Track B while covering all four capabilities cleanly.

**Grounding against hallucination** - the LLM receives the actual asset data in every prompt. System prompts explicitly instruct the model not to invent assets. For `mode=query`, results are assets from the database matched by the model, not model-generated text.

**LangChain chains** - each mode uses a `ChatPromptTemplate | LLM | OutputParser` chain. `JsonOutputParser` enforces structured output with automatic retry on parse failure.

**Claude Haiku** - fast and cheap for the structured classification tasks. Can be swapped to `claude-opus-4-8` in `app/chains/analyze.py` for higher quality.

**Idempotent import** - same logic as Track A: upsert on `(type, value)`, merge tags (union), merge metadata (incoming overwrites), re-activate stale assets.

**Auto-enrichment persistence** - `mode=enrich` writes `env_category` and `criticality` back to the database so subsequent queries and reports reflect the enrichment.

**Error handling** - LLM failures return structured error responses, never crash the API. Invalid `mode` values return 400. Missing required fields (e.g. `asset_id` for enrich) return 400.

---

## Assumptions

- No authentication on endpoints - in production this would require API key auth (see Track A for full auth implementation).
- The LLM is trusted to follow grounding instructions; for production, add a post-processing step that verifies returned asset IDs exist in the database.
- `mode=enrich` enriches one asset at a time; bulk enrichment would be a simple loop over all assets.
- Relationship data from the import (`parent`, `covers`, `resolves_to`) is stored but not yet exposed via API endpoints - focus is on the four analysis capabilities.
