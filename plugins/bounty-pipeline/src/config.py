"""Configuration loader for bounty-pipeline.

Loads ~/.bounty-pipeline/config.yaml and merges environment variable overrides.
Env vars use BOUNTY_PIPELINE_ prefix with double-underscore for nesting:
  BOUNTY_PIPELINE_SERVICES__RETICUSTOS__URL=http://localhost:9000
"""

import os
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path.home() / ".bounty-pipeline" / "config.yaml"

DEFAULT_CONFIG = {
    "services": {
        "reticustos": {"url": "http://localhost:8002", "timeout": 600, "poll_interval": 15},
        "mobilicustos": {"url": "http://localhost:8000", "timeout": 900, "poll_interval": 15},
        "nubicustos": {"url": "http://localhost:8001", "timeout": 1800, "poll_interval": 30},
    },
    "tools": {
        "indago": "~/GitHub/indago/indago",
        "burrito": "~/GitHub/bypassburrito/burrito",
        "cepheus": "~/GitHub/Cepheus/.venv/bin/cepheus",
        "vinculum": "~/GitHub/vinculum/.venv/bin/vinculum",
        "ariadne": "~/GitHub/ariadne/.venv/bin/ariadne",
    },
    "llm": {"provider": "anthropic"},
    "defaults": {
        "reticustos_profile": "standard",
        "nubicustos_profile": "comprehensive",
        "mobilicustos_scan_type": "full",
    },
    "workspace": {"root": "~/.bounty-pipeline/runs"},
    "docker": {
        "reticustos": "~/GitHub/Reticustos",
        "mobilicustos": "~/GitHub/mobilicustos",
        "nubicustos": "~/GitHub/Nubicustos",
    },
}

ENV_PREFIX = "BOUNTY_PIPELINE_"


def _expand_paths(config: dict) -> dict:
    """Recursively expand ~ in string values that look like paths."""
    result = {}
    for key, value in config.items():
        if isinstance(value, dict):
            result[key] = _expand_paths(value)
        elif isinstance(value, str) and ("~" in value or value.startswith("/")):
            result[key] = str(Path(value).expanduser())
        else:
            result[key] = value
    return result


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base, returning new dict."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _apply_env_overrides(config: dict) -> dict:
    """Apply BOUNTY_PIPELINE_* environment variable overrides.

    Double underscores denote nesting:
      BOUNTY_PIPELINE_SERVICES__RETICUSTOS__URL -> config["services"]["reticustos"]["url"]
    """
    for env_key, env_value in os.environ.items():
        if not env_key.startswith(ENV_PREFIX):
            continue
        parts = env_key[len(ENV_PREFIX) :].lower().split("__")
        target = config
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        # Try numeric conversion
        try:
            env_value = int(env_value)
        except ValueError:
            try:
                env_value = float(env_value)
            except ValueError:
                pass
        target[parts[-1]] = env_value
    return config


def load_config(config_path: str | Path | None = None) -> dict:
    """Load and validate pipeline configuration.

    Priority: env vars > config file > defaults.
    """
    config = DEFAULT_CONFIG.copy()

    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if path.exists():
        with open(path) as f:
            file_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, file_config)

    config = _apply_env_overrides(config)
    config = _expand_paths(config)

    return config


def get_service_config(config: dict, service_name: str) -> dict:
    """Get configuration for a specific service."""
    return config.get("services", {}).get(service_name, {})


def get_tool_path(config: dict, tool_name: str) -> str:
    """Get expanded path for a CLI tool."""
    return config.get("tools", {}).get(tool_name, tool_name)


def get_workspace_root(config: dict) -> Path:
    """Get the workspace root directory."""
    return Path(config.get("workspace", {}).get("root", "~/.bounty-pipeline/runs")).expanduser()


def get_docker_path(config: dict, service_name: str) -> Path:
    """Get the Docker Compose project directory for a service."""
    path = config.get("docker", {}).get(service_name, "")
    return Path(path).expanduser() if path else Path()
