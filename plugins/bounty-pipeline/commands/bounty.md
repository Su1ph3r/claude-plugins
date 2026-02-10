---
description: "End-to-end bug bounty pipeline — orchestrates Reticustos, Indago, BypassBurrito, Mobilicustos, Nubicustos, Cepheus, Vinculum, and Ariadne through agent-driven phases from recon to attack path synthesis"
argument-hint: "<type> <target> [--dry-run] [--resume <run-id>] [--skip <phases>] [--spec <file>] [--app-id <id>] [--profile <name>]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Task"]
---

# Bounty Pipeline Orchestrator

Run an end-to-end bug bounty pipeline against a target. Each phase launches specialist agents that execute security tools, with outputs flowing between phases via cross-tool data connectors.

**Arguments:** "$ARGUMENTS"

## Phase 0: Setup

### Parse Arguments

Parse "$ARGUMENTS" to extract:

- **`<type>`** (required, first arg): Pipeline type — `web`, `mobile`, `cloud`, `full`, `api`
- **`<target>`** (required, second arg): Target identifier — domain, IP, app ID, cloud account, or API spec path
- **`--dry-run`**: Show pipeline plan without executing
- **`--resume <path>`**: Resume from an existing workspace
- **`--skip <phases>`**: Comma-separated phase names to skip (e.g., `--skip waf-bypass,container-escape`)
- **`--spec <file>`**: OpenAPI/Swagger spec for API fuzzing (used by api-fuzz-agent)
- **`--app-id <id>`**: Mobile app ID for Mobilicustos (required for `mobile` and `full` types)
- **`--profile <name>`**: Scan profile override (default varies by tool)

Pipeline types and what they run:
```
web:    recon → api-fuzz → waf-bypass → correlate → attack-paths
mobile: mobile-scan → correlate → attack-paths
cloud:  cloud-audit → container-escape → correlate → attack-paths
full:   [recon + mobile-scan + cloud-audit] → [api-fuzz + container-escape] → waf-bypass → correlate → attack-paths
api:    api-fuzz → waf-bypass → correlate → attack-paths
```

### Validate & Configure

1. Load the pipeline config by running:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/src/orchestrator.py check-services --type <type>
```

2. If any required services are down, show the user the start commands and **stop**. Do NOT proceed with services down.

3. If `--resume` was provided, load the existing workspace. Otherwise, create a new one:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/src/orchestrator.py init-workspace --target <target> --type <type>
```

4. Extract the workspace path from the output (look for `__WORKSPACE_JSON__:` line).

5. Store these values for all subsequent phases:
   - `WORKSPACE` — the workspace directory path
   - `TARGET` — the target identifier
   - `TYPE` — the pipeline type
   - Tool paths from config:
     - Reticustos URL: `http://localhost:8002` (or from config)
     - Mobilicustos URL: `http://localhost:8000` (or from config)
     - Nubicustos URL: `http://localhost:8001` (or from config)
     - `INDAGO_PATH`: `~/GitHub/indago/indago`
     - `BURRITO_PATH`: `~/GitHub/bypassburrito/burrito`
     - `CEPHEUS_PATH`: `~/GitHub/Cepheus/.venv/bin/cepheus`
     - `VINCULUM_PATH`: `~/GitHub/vinculum/.venv/bin/vinculum`
     - `ARIADNE_PATH`: `~/GitHub/ariadne/.venv/bin/ariadne`

6. If `--dry-run`, show the full pipeline plan (which agents run in which order) and **stop**.

Announce to the user:
```
Pipeline: <type>
Target: <target>
Workspace: <workspace_path>
Phases: <list of phases that will run>
```

## Phase 1: Initial Scanning

Launch the initial scanning agents based on the pipeline type. Launch all agents for this phase **in parallel** (send ALL Task calls in a single response).

### Agent context template

Every agent prompt MUST include this context block:
```
Target: <TARGET>
Workspace: <WORKSPACE>
Pipeline type: <TYPE>

Service URLs:
- Reticustos: <RETICUSTOS_URL>
- Mobilicustos: <MOBILICUSTOS_URL>
- Nubicustos: <NUBICUSTOS_URL>

Tool paths:
- Indago: <INDAGO_PATH>
- BypassBurrito: <BURRITO_PATH>
- Cepheus: <CEPHEUS_PATH>
- Vinculum: <VINCULUM_PATH>
- Ariadne: <ARIADNE_PATH>

[Any additional context specific to this agent]
```

### Which agents to launch

| Type | Phase 1 agents (parallel) |
|------|--------------------------|
| `web` | `recon-agent` |
| `mobile` | `mobile-scan-agent` (with `--app-id`) |
| `cloud` | `cloud-audit-agent` |
| `full` | `recon-agent` + `mobile-scan-agent` + `cloud-audit-agent` (all parallel) |
| `api` | `api-fuzz-agent` (with `--spec` if provided) |

For each agent, use the Task tool with:
- `subagent_type`: `bounty-pipeline:<agent-name>` (e.g., `bounty-pipeline:recon-agent`)
- `model`: `opus`
- Include the full context block in the prompt

Wait for all agents to complete. Collect results.

After Phase 1 completes, update the workspace:
```bash
python3 -c "
import json; from pathlib import Path
ws = Path('WORKSPACE')
meta = json.loads((ws/'run-meta.json').read_text())
meta['status'] = 'phase1_complete'
meta['phases_completed'].append('scanning')
(ws/'run-meta.json').write_text(json.dumps(meta, indent=2))
"
```

Announce: "Phase 1 complete. [Summary of scanning results]"

## Phase 2: Secondary Analysis

Launch secondary analysis agents that depend on Phase 1 outputs. Launch all agents for this phase **in parallel**.

| Type | Phase 2 agents |
|------|---------------|
| `web` | `api-fuzz-agent` (using `reticustos-endpoints.json` via `--targets-from`) |
| `mobile` | (skip — go directly to Phase 4) |
| `cloud` | `container-escape-agent` (using `nubicustos-containers.json`) |
| `full` | `api-fuzz-agent` + `container-escape-agent` (parallel) |
| `api` | (skip — api-fuzz already ran in Phase 1, go to Phase 3) |

For `web` and `full` types, the `api-fuzz-agent` prompt must include:
```
Use --targets-from WORKSPACE/reticustos-endpoints.json instead of --spec.
```

For `cloud` and `full` types, the `container-escape-agent` prompt must include:
```
Use --from-nubicustos WORKSPACE/nubicustos-containers.json for cloud context.
```

Wait for all agents to complete. Announce: "Phase 2 complete. [Summary]"

## Phase 3: WAF Bypass (Conditional)

This phase is **conditional** — only runs if `waf-blocked.json` exists in the workspace AND has entries.

Check:
```bash
python3 -c "
import json, pathlib, sys
p = pathlib.Path('WORKSPACE/waf-blocked.json')
if not p.exists():
    print('SKIP: No waf-blocked.json found')
    sys.exit(0)
data = json.loads(p.read_text())
total = data.get('total_blocked', 0)
if total == 0:
    print('SKIP: Zero WAF-blocked targets')
else:
    print(f'PROCEED: {total} WAF-blocked targets to bypass')
"
```

If SKIP: Announce "No WAF-blocked findings. Skipping WAF bypass phase." and proceed to Phase 4.

If PROCEED: Launch `waf-bypass-agent` with:
- `subagent_type`: `bounty-pipeline:waf-bypass-agent`
- `model`: `opus`
- Include workspace path and tool paths in context

Wait for completion. Announce: "Phase 3 complete. [Bypass results summary]"

## Phase 4: Correlation

Launch the `correlation-agent` to ingest ALL reports from the workspace.

Agent prompt must include:
```
Ingest all *-findings.json and *-report.json files in the workspace.
Export both ariadne format (vinculum-ariadne.json) and json format (vinculum-correlated.json).
```

Use:
- `subagent_type`: `bounty-pipeline:correlation-agent`
- `model`: `opus`

Wait for completion. Announce: "Phase 4 complete. [Correlation summary]"

## Phase 5: Attack Path Synthesis

Launch the `attack-path-agent` to synthesize attack paths from correlated findings.

Verify `vinculum-ariadne.json` exists first. If not, skip this phase.

Agent prompt must include:
```
Analyze WORKSPACE/vinculum-ariadne.json with --playbook --sprawl --privesc.
Output to WORKSPACE/ariadne-report.json.
```

Use:
- `subagent_type`: `bounty-pipeline:attack-path-agent`
- `model`: `opus`

Wait for completion. Announce: "Phase 5 complete. [Attack path summary]"

## Phase 6: Final Report

Read the key output files from the workspace and present a comprehensive report:

```bash
ls -la WORKSPACE/*.json | grep -v run-meta
```

Read the following files (as available):
- `vinculum-correlated.json` — for finding summary
- `ariadne-report.json` — for attack paths
- `burrito-report.json` — for WAF bypass results

Present the final report in this structure:

```markdown
# Bounty Pipeline Report

## Target Summary
- **Target**: <target>
- **Pipeline**: <type>
- **Workspace**: <workspace_path>
- **Duration**: <time from start to finish>

## Findings Overview
| Severity | Count |
|----------|-------|
| Critical | N |
| High | N |
| Medium | N |
| Low | N |
| Info | N |

## Tool Results
| Tool | Findings | Key Results |
|------|----------|-------------|
| Reticustos | N endpoints, N findings | ... |
| Indago | N vulns, N WAF-blocked | ... |
| BypassBurrito | N bypasses found | ... |
| Mobilicustos | N findings | ... |
| Nubicustos | N findings, N containers | ... |
| Cepheus | N escape paths | ... |

## Cross-Tool Correlations
[Findings confirmed by multiple tools]

## Attack Paths
[Top attack chains from Ariadne, with step-by-step descriptions]

## Recommendations
1. [Prioritized by severity and exploitability]
2. ...

## Workspace Files
[List of all output files with sizes]
```

Update workspace status to "completed":
```bash
python3 -c "
import json; from pathlib import Path
ws = Path('WORKSPACE')
meta = json.loads((ws/'run-meta.json').read_text())
meta['status'] = 'completed'
meta['phases_completed'].append('report')
(ws/'run-meta.json').write_text(json.dumps(meta, indent=2))
"
```

## Quick Reference

| Invocation | Behavior |
|---|---|
| `/bounty web example.com` | Full web pipeline: recon → fuzz → bypass → correlate → paths |
| `/bounty api --spec api.yaml` | API-only: fuzz → bypass → correlate → paths |
| `/bounty mobile --app-id com.example.app` | Mobile: scan → correlate → paths |
| `/bounty cloud aws-account-id` | Cloud: audit → containers → correlate → paths |
| `/bounty full example.com --app-id com.app` | Everything in parallel where possible |
| `/bounty web example.com --dry-run` | Show plan without executing |
| `/bounty web example.com --skip waf-bypass` | Skip the WAF bypass phase |
| `/bounty web example.com --resume ~/.bounty-pipeline/runs/...` | Resume a previous run |

## Important Notes

- Always use `model: "opus"` for all agent Task calls
- Always launch agents in parallel when the pipeline allows (multiple Task calls in ONE response)
- The correlation and attack-path agents run AFTER all scanning agents, not in parallel with them
- WAF bypass is conditional — only runs when there are actually WAF-blocked findings
- Each agent writes its outputs to the shared workspace directory
- All cross-tool data connectors are file-based JSON — agents produce files, next agents consume them
- If an agent fails, report the failure clearly but continue with remaining phases where possible
- Announce progress to the user at each phase transition
