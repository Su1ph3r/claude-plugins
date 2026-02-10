"""Pipeline DAG definitions for bounty-pipeline.

Defines which agents run in which order per target type.
Each phase is a list of agents that can run in parallel.
Phases execute sequentially.
"""

# Agent identifiers match the agent filenames (without .md)
AGENTS = {
    "recon": "recon-agent",
    "api-fuzz": "api-fuzz-agent",
    "waf-bypass": "waf-bypass-agent",
    "mobile-scan": "mobile-scan-agent",
    "cloud-audit": "cloud-audit-agent",
    "container-escape": "container-escape-agent",
    "correlate": "correlation-agent",
    "attack-paths": "attack-path-agent",
}

# Pipeline DAGs per target type.
# Each entry is a list of phases. Each phase is a list of agent keys.
# Phases run sequentially; agents within a phase run in parallel.
PIPELINES = {
    "web": [
        ["recon"],
        ["api-fuzz"],
        ["waf-bypass"],  # conditional — skipped if no waf-blocked findings
        ["correlate"],
        ["attack-paths"],
    ],
    "mobile": [
        ["mobile-scan"],
        ["correlate"],
        ["attack-paths"],
    ],
    "cloud": [
        ["cloud-audit"],
        ["container-escape"],
        ["correlate"],
        ["attack-paths"],
    ],
    "full": [
        ["recon", "mobile-scan", "cloud-audit"],
        ["api-fuzz", "container-escape"],
        ["waf-bypass"],  # conditional
        ["correlate"],
        ["attack-paths"],
    ],
    "api": [
        ["api-fuzz"],
        ["waf-bypass"],  # conditional
        ["correlate"],
        ["attack-paths"],
    ],
}

# Maps agent keys to the Docker services they require
AGENT_SERVICE_DEPS = {
    "recon": ["reticustos"],
    "api-fuzz": [],  # CLI tool
    "waf-bypass": [],  # CLI tool
    "mobile-scan": ["mobilicustos"],
    "cloud-audit": ["nubicustos"],
    "container-escape": [],  # CLI tool
    "correlate": [],  # CLI tool
    "attack-paths": [],  # CLI tool
}

# Maps agent keys to the workspace files they produce
AGENT_OUTPUTS = {
    "recon": ["reticustos-findings.json", "reticustos-endpoints.json"],
    "api-fuzz": ["indago-report.json", "waf-blocked.json"],
    "waf-bypass": ["burrito-report.json"],
    "mobile-scan": ["mobilicustos-findings.json"],
    "cloud-audit": ["nubicustos-findings.json", "nubicustos-containers.json"],
    "container-escape": ["cepheus-report.json"],
    "correlate": ["vinculum-correlated.json", "vinculum-ariadne.json"],
    "attack-paths": ["ariadne-report.json"],
}

# Maps agent keys to workspace files they consume (from previous phases)
AGENT_INPUTS = {
    "recon": [],
    "api-fuzz": ["reticustos-endpoints.json"],  # optional: --targets-from
    "waf-bypass": ["waf-blocked.json"],
    "mobile-scan": [],
    "cloud-audit": [],
    "container-escape": ["nubicustos-containers.json"],
    "correlate": [],  # ingests all *.json reports in workspace
    "attack-paths": ["vinculum-ariadne.json"],
}


def get_pipeline(target_type: str) -> list[list[str]]:
    """Get the pipeline phases for a target type."""
    if target_type not in PIPELINES:
        raise ValueError(f"Unknown target type: {target_type}. Valid: {list(PIPELINES.keys())}")
    return PIPELINES[target_type]


def get_agent_id(agent_key: str) -> str:
    """Get the full agent identifier for Task tool subagent_type."""
    return f"bounty-pipeline:{AGENTS[agent_key]}"


def get_required_services(target_type: str) -> list[str]:
    """Get all Docker services required for a pipeline."""
    pipeline = get_pipeline(target_type)
    services = set()
    for phase in pipeline:
        for agent_key in phase:
            services.update(AGENT_SERVICE_DEPS.get(agent_key, []))
    return sorted(services)


def describe_pipeline(target_type: str) -> str:
    """Return a human-readable description of a pipeline."""
    pipeline = get_pipeline(target_type)
    lines = [f"Pipeline: {target_type}\n"]
    for i, phase in enumerate(pipeline):
        agent_names = [AGENTS[k] for k in phase]
        parallel = " + ".join(agent_names)
        lines.append(f"  Phase {i + 1}: {parallel}")
    return "\n".join(lines)
