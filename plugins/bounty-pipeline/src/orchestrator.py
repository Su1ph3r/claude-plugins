#!/usr/bin/env python3
"""Bounty Pipeline orchestrator CLI.

Utility commands for service checks, workspace management, and status.
The actual pipeline flow is driven by the /bounty command + Task tool agents.

Usage:
    python3 orchestrator.py check-services --type web
    python3 orchestrator.py init-workspace --target example.com --type web
    python3 orchestrator.py status [--workspace <path>]
    python3 orchestrator.py list-runs [--limit 10]
"""

import argparse
import json
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from docker_check import check_cli_tools, check_services, format_status_report
from pipeline import describe_pipeline, get_required_services
from workspace import create_workspace, list_workspaces, load_workspace


def cmd_check_services(args, config):
    """Check Docker services and CLI tools for a target type."""
    target_type = args.type
    required = get_required_services(target_type)

    print(f"Checking services for pipeline type: {target_type}")
    print(f"Required Docker services: {required or 'none'}\n")

    service_results = check_services(config, target_type)
    tool_results = check_cli_tools(config)

    print(format_status_report(service_results, tool_results))

    # Exit code: 0 if all required services healthy, 1 otherwise
    all_ok = all(s["healthy"] for s in service_results.values())
    tools_ok = all(t["executable"] for t in tool_results.values())

    if not all_ok:
        print("\nSome required services are not running. Start them before proceeding.")
        sys.exit(1)
    if not tools_ok:
        missing = [n for n, t in tool_results.items() if not t["executable"]]
        print(f"\nMissing CLI tools: {', '.join(missing)}")
        sys.exit(1)

    print("\nAll checks passed.")


def cmd_init_workspace(args, config):
    """Initialize a new run workspace."""
    workspace = create_workspace(config, args.target, args.type)
    print(f"Workspace created: {workspace}")
    print(f"Pipeline: {args.type}")
    print(describe_pipeline(args.type))

    # Output workspace path as JSON for machine consumption
    result = {"workspace": str(workspace), "target": args.target, "type": args.type}
    print(f"\n__WORKSPACE_JSON__:{json.dumps(result)}")


def cmd_status(args, config):
    """Show status of a workspace or the latest run."""
    if args.workspace:
        ws_path = Path(args.workspace).expanduser()
    else:
        from workspace import find_latest_workspace
        ws_path = find_latest_workspace(config)
        if not ws_path:
            print("No workspaces found.")
            sys.exit(1)

    meta = load_workspace(ws_path)
    print(f"Workspace: {meta.get('path', ws_path)}")
    print(f"Target: {meta['target']}")
    print(f"Type: {meta['target_type']}")
    print(f"Status: {meta['status']}")
    print(f"Created: {meta['created_at']}")
    print(f"Phases completed: {', '.join(meta.get('phases_completed', [])) or 'none'}")

    # List output files
    outputs = list(ws_path.glob("*.json"))
    outputs = [f for f in outputs if f.name != "run-meta.json"]
    if outputs:
        print(f"\nOutput files ({len(outputs)}):")
        for f in sorted(outputs):
            size = f.stat().st_size
            print(f"  {f.name} ({size:,} bytes)")


def cmd_list_runs(args, config):
    """List recent pipeline runs."""
    runs = list_workspaces(config, limit=args.limit)
    if not runs:
        print("No runs found.")
        return

    print(f"Recent runs ({len(runs)}):\n")
    for run in runs:
        status = run.get("status", "unknown")
        phases = len(run.get("phases_completed", []))
        print(f"  {run['target']} [{run['target_type']}] — {status} ({phases} phases)")
        print(f"    {run.get('path', 'unknown')}")
        print(f"    Created: {run['created_at']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Bounty Pipeline Orchestrator")
    parser.add_argument("--config", help="Config file path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check-services
    check_parser = subparsers.add_parser("check-services", help="Check required services")
    check_parser.add_argument("--type", required=True, choices=["web", "mobile", "cloud", "full", "api"])

    # init-workspace
    init_parser = subparsers.add_parser("init-workspace", help="Create a run workspace")
    init_parser.add_argument("--target", required=True, help="Target identifier")
    init_parser.add_argument("--type", required=True, choices=["web", "mobile", "cloud", "full", "api"])

    # status
    status_parser = subparsers.add_parser("status", help="Show run status")
    status_parser.add_argument("--workspace", help="Workspace path (default: latest)")

    # list-runs
    list_parser = subparsers.add_parser("list-runs", help="List recent runs")
    list_parser.add_argument("--limit", type=int, default=10, help="Max runs to show")

    args = parser.parse_args()
    config = load_config(args.config)

    commands = {
        "check-services": cmd_check_services,
        "init-workspace": cmd_init_workspace,
        "status": cmd_status,
        "list-runs": cmd_list_runs,
    }
    commands[args.command](args, config)


if __name__ == "__main__":
    main()
