"""Workspace management for bounty-pipeline runs.

Each /bounty invocation creates a workspace at:
  ~/.bounty-pipeline/runs/<target>-<timestamp>/

Contains all intermediate JSON files, enables resumability.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from config import get_workspace_root


def _sanitize_target(target: str) -> str:
    """Sanitize target string for use as directory name."""
    sanitized = re.sub(r"[^\w\-.]", "_", target)
    return sanitized[:80]


def create_workspace(config: dict, target: str, target_type: str) -> Path:
    """Create a new run workspace directory.

    Returns the workspace path.
    """
    root = get_workspace_root(config)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_target = _sanitize_target(target)
    workspace = root / f"{safe_target}-{timestamp}"
    workspace.mkdir(parents=True, exist_ok=True)

    meta = {
        "target": target,
        "target_type": target_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "initialized",
        "phases_completed": [],
        "workspace": str(workspace),
    }
    (workspace / "run-meta.json").write_text(json.dumps(meta, indent=2))

    return workspace


def load_workspace(workspace_path: str | Path) -> dict:
    """Load run metadata from an existing workspace."""
    path = Path(workspace_path)
    meta_file = path / "run-meta.json"
    if not meta_file.exists():
        raise FileNotFoundError(f"No run-meta.json found in {path}")
    return json.loads(meta_file.read_text())


def update_workspace_status(workspace: Path, status: str, phase: str | None = None) -> None:
    """Update workspace run metadata."""
    meta_file = workspace / "run-meta.json"
    meta = json.loads(meta_file.read_text())
    meta["status"] = status
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    if phase and phase not in meta["phases_completed"]:
        meta["phases_completed"].append(phase)
    meta_file.write_text(json.dumps(meta, indent=2))


def save_checkpoint(workspace: Path, phase: str, data: dict) -> Path:
    """Save a phase checkpoint for resumability."""
    checkpoint_dir = workspace / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    checkpoint_file = checkpoint_dir / f"{phase}.json"
    checkpoint_data = {
        "phase": phase,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    checkpoint_file.write_text(json.dumps(checkpoint_data, indent=2))
    return checkpoint_file


def load_checkpoint(workspace: Path, phase: str) -> dict | None:
    """Load a phase checkpoint if it exists."""
    checkpoint_file = workspace / "checkpoints" / f"{phase}.json"
    if checkpoint_file.exists():
        return json.loads(checkpoint_file.read_text())
    return None


def find_latest_workspace(config: dict, target: str | None = None) -> Path | None:
    """Find the most recent workspace, optionally filtered by target."""
    root = get_workspace_root(config)
    if not root.exists():
        return None
    workspaces = sorted(root.iterdir(), reverse=True)
    for ws in workspaces:
        if not ws.is_dir():
            continue
        if target:
            safe = _sanitize_target(target)
            if not ws.name.startswith(safe):
                continue
        meta_file = ws / "run-meta.json"
        if meta_file.exists():
            return ws
    return None


def list_workspaces(config: dict, limit: int = 10) -> list[dict]:
    """List recent workspaces with metadata."""
    root = get_workspace_root(config)
    if not root.exists():
        return []
    results = []
    for ws in sorted(root.iterdir(), reverse=True):
        if not ws.is_dir():
            continue
        meta_file = ws / "run-meta.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            meta["path"] = str(ws)
            results.append(meta)
            if len(results) >= limit:
                break
    return results
