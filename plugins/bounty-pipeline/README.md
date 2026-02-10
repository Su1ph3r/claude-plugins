# bounty-pipeline

Claude Code plugin that orchestrates 8 security tools into an end-to-end bug bounty hunting pipeline.

## Tools

| Tool | Type | Purpose |
|------|------|---------|
| Reticustos | Docker/REST | Network reconnaissance |
| Indago | CLI (Go) | AI-powered API fuzzing |
| BypassBurrito | CLI (Go) | LLM-powered WAF bypass |
| Mobilicustos | Docker/REST | Mobile app security |
| Nubicustos | Docker/REST | Cloud security audit |
| Cepheus | CLI (Python) | Container escape modeling |
| Vinculum | CLI (Python) | Finding correlation |
| Ariadne | CLI (Python) | Attack path synthesis |

## Pipeline Types

```
web:    recon --> api-fuzz --> waf-bypass --> correlate --> attack-paths
mobile: mobile-scan --> correlate --> attack-paths
cloud:  cloud-audit --> container-escape --> correlate --> attack-paths
full:   [recon + mobile + cloud] --> [api-fuzz + containers] --> waf-bypass --> correlate --> attack-paths
api:    api-fuzz --> waf-bypass --> correlate --> attack-paths
```

## Cross-Tool Data Flow

```
Reticustos (endpoints.json) ----> Indago (--targets-from)
                                      |
                                      | (waf-blocked.json)
                                      v
                                  BypassBurrito (--from-indago)

Nubicustos (containers.json) ---> Cepheus (--from-nubicustos)

ALL tool outputs ----------------> Vinculum (auto-detect parsers)
                                      |
                                      | (--format ariadne)
                                      v
                                  Ariadne (attack path synthesis)
```

## Usage

```
/bounty web example.com                          # Full web pipeline
/bounty api --spec openapi.yaml                   # API-only pipeline
/bounty mobile --app-id com.example.app           # Mobile analysis
/bounty cloud aws-account-id                      # Cloud audit
/bounty full example.com --app-id com.example.app # Everything
/bounty web example.com --dry-run                 # Show plan only
/bounty web example.com --skip waf-bypass         # Skip a phase
/bounty web example.com --resume <workspace>      # Resume a run
```

## Prerequisites

### Docker Services
- Reticustos running on port 8002
- Mobilicustos running on port 8000
- Nubicustos running on port 8001

### CLI Tools
- `~/GitHub/indago/indago` (Go binary)
- `~/GitHub/bypassburrito/burrito` (Go binary)
- `~/GitHub/Cepheus/.venv/bin/cepheus` (Python)
- `~/GitHub/vinculum/.venv/bin/vinculum` (Python)
- `~/GitHub/ariadne/.venv/bin/ariadne` (Python)

## Configuration

Default config at `~/.bounty-pipeline/config.yaml`. Override with environment variables using `BOUNTY_PIPELINE_` prefix:

```
BOUNTY_PIPELINE_SERVICES__RETICUSTOS__URL=http://localhost:9000
```

## Workspace

Each run creates `~/.bounty-pipeline/runs/<target>-<timestamp>/` containing all intermediate JSON files. Supports resumability via `--resume`.

## Verification

```bash
# Check services
python3 ~/.claude/plugins/local/bounty-pipeline/src/orchestrator.py check-services --type web

# Init workspace
python3 ~/.claude/plugins/local/bounty-pipeline/src/orchestrator.py init-workspace --target test --type web

# List runs
python3 ~/.claude/plugins/local/bounty-pipeline/src/orchestrator.py list-runs
```
