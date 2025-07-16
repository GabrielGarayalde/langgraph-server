# Google Sheets Integration Setup Guide

## Quick Start - Where to Put Your Credentials

### 1. Copy Your Service Account JSON
```bash
# From your experiments folder to the backend
cp experiments/google_sheets/credentials/service_account.json backend/credentials/service_account.json
```

### 2. Create/Update Backend .env File
Add these lines to `backend/.env`:
```bash
# Google Sheets Configuration
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SERVICE_ACCOUNT_PATH=./credentials/service_account.json
GOOGLE_SHEETS_CACHE_TTL=3600
GOOGLE_SHEETS_DEFAULT_TIMEOUT=30

# Your existing test sheet ID
STEEL_BEAM_SHEET_ID=1yWPRmYfHlQ9zpkQQSfsxCnk0u0rVPXrJqec6Le48Wgs
```

## Implementation Phases

### Phase 1: Basic Integration (Today)
1. ✅ Create credentials directory structure
2. ⏳ Copy service account JSON to `backend/credentials/`
3. ⏳ Create sheets calculator service
4. ⏳ Add as LangGraph tool

### Phase 2: Calculator Configurations
Create calculator configs in `backend/configs/calculators/`:

**steel_beam.json:**
```json
{
  "name": "steel_beam",
  "description": "AS 4100 Steel Beam Calculator",
  "sheet_id": "1yWPRmYfHlQ9zpkQQSfsxCnk0u0rVPXrJqec6Le48Wgs",
  "inputs": {
    "beam_length": "B4",
    "applied_load": "B5",
    "steel_grade": "B6"
  },
  "outputs": {
    "max_moment": "D4",
    "max_deflection": "D5",
    "utilization_ratio": "D6",
    "safety_factor": "D7",
    "compliance": "D9"
  }
}
```

### Phase 3: LangGraph Tool Integration
The tool will be added to `backend/src/react_agent/tools.py` and will:
- Load calculator configurations
- Authenticate with Google Sheets
- Execute calculations
- Return results to the agent

## Next Steps

1. **Copy Credentials:**
   ```bash
   cp experiments/google_sheets/credentials/service_account.json backend/credentials/
   ```

2. **Test Connection:**
   Run your existing test to verify credentials work:
   ```bash
   cd experiments/google_sheets
   python test_practical_approach.py
   ```

3. **Start Integration:**
   I'll help you create the calculator service and LangGraph tool

## Security Checklist
- [ ] Service account JSON copied to `backend/credentials/`
- [ ] `.gitignore` verified to exclude credentials
- [ ] Environment variables set in `.env`
- [ ] Never commit credentials to git

## File Locations Summary
```
Your Credentials Should Go Here:
└── backend/
    ├── credentials/
    │   └── service_account.json  ← COPY YOUR JSON HERE
    ├── .env                      ← ADD GOOGLE_SHEETS CONFIG
    └── configs/
        └── calculators/
            └── steel_beam.json   ← CALCULATOR CONFIGS
```

## Questions?
- Your test sheet ID is ready: `1yWPRmYfHlQ9zpkQQSfsxCnk0u0rVPXrJqec6Le48Wgs`
- The integration will use the same approach as your working `test_practical_approach.py`
- Engineers can continue modifying formulas in Google Sheets