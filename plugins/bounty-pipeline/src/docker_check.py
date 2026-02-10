"""Docker service health checker for bounty-pipeline.

Checks if Docker Compose services are running and their API endpoints respond.
"""

import json
import subprocess
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from config import get_docker_path, get_service_config

# Which Docker services are needed per target type
SERVICES_BY_TYPE = {
    "web": ["reticustos"],
    "mobile": ["mobilicustos"],
    "cloud": ["nubicustos"],
    "full": ["reticustos", "mobilicustos", "nubicustos"],
    "api": [],  # API-only uses CLI tools, no Docker services
}


def check_docker_running(compose_dir: Path) -> tuple[bool, str]:
    """Check if Docker Compose services are running in the given directory."""
    if not compose_dir.exists():
        return False, f"Directory not found: {compose_dir}"
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            cwd=compose_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False, f"docker compose ps failed: {result.stderr.strip()}"
        if not result.stdout.strip():
            return False, "No containers running"
        # Parse JSON lines output
        containers = []
        for line in result.stdout.strip().splitlines():
            try:
                containers.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        running = [c for c in containers if c.get("State") == "running"]
        if not running:
            return False, "Containers exist but none are running"
        return True, f"{len(running)} container(s) running"
    except FileNotFoundError:
        return False, "docker command not found"
    except subprocess.TimeoutExpired:
        return False, "docker compose ps timed out"


def check_api_health(base_url: str, timeout: int = 5) -> tuple[bool, str]:
    """Check if an API service responds to health check."""
    health_url = f"{base_url.rstrip('/')}/api/health"
    try:
        req = Request(health_url, method="GET")
        with urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return True, "API healthy"
            return False, f"API returned status {resp.status}"
    except URLError as e:
        return False, f"API unreachable: {e.reason}"
    except Exception as e:
        return False, f"API check failed: {e}"


def check_services(config: dict, target_type: str) -> dict:
    """Check all required services for a target type.

    Returns dict with service name -> {running, healthy, message, start_cmd}.
    """
    required = SERVICES_BY_TYPE.get(target_type, [])
    results = {}

    for service_name in required:
        svc_config = get_service_config(config, service_name)
        docker_dir = get_docker_path(config, service_name)
        base_url = svc_config.get("url", "")

        docker_ok, docker_msg = check_docker_running(docker_dir)
        api_ok, api_msg = False, "Not checked"
        if docker_ok:
            api_ok, api_msg = check_api_health(base_url)

        start_cmd = f"cd {docker_dir} && docker compose up -d"

        results[service_name] = {
            "running": docker_ok,
            "healthy": api_ok,
            "docker_message": docker_msg,
            "api_message": api_msg,
            "start_cmd": start_cmd,
            "url": base_url,
        }

    return results


def check_cli_tools(config: dict) -> dict:
    """Check if CLI tools are installed and accessible."""
    tools = config.get("tools", {})
    results = {}

    for name, path in tools.items():
        expanded = str(Path(path).expanduser())
        exists = Path(expanded).exists()
        executable = Path(expanded).is_file() and (Path(expanded).stat().st_mode & 0o111)

        results[name] = {
            "path": expanded,
            "exists": exists,
            "executable": bool(executable) if exists else False,
        }

    return results


def format_status_report(service_results: dict, tool_results: dict) -> str:
    """Format a human-readable status report."""
    lines = ["## Service Status\n"]

    if not service_results:
        lines.append("No Docker services required for this target type.\n")
    else:
        for name, info in service_results.items():
            status = "OK" if info["healthy"] else ("RUNNING (unhealthy)" if info["running"] else "DOWN")
            lines.append(f"- **{name}**: {status}")
            if not info["running"]:
                lines.append(f"  - Start: `{info['start_cmd']}`")
            elif not info["healthy"]:
                lines.append(f"  - API: {info['api_message']}")
            lines.append("")

    lines.append("## CLI Tools\n")
    for name, info in tool_results.items():
        status = "OK" if info["executable"] else ("EXISTS (not executable)" if info["exists"] else "NOT FOUND")
        lines.append(f"- **{name}**: {status} — `{info['path']}`")

    return "\n".join(lines)
