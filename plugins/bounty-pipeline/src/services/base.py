"""Base classes for bounty-pipeline service clients.

RESTServiceClient: for Docker-based FastAPI services (Reticustos, Mobilicustos, Nubicustos).
CLIToolWrapper: for local CLI tools (Indago, BypassBurrito, Cepheus, Vinculum, Ariadne).
"""

import json
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class RESTServiceClient:
    """Base client for FastAPI REST services running in Docker."""

    def __init__(self, base_url: str, timeout: int = 600, poll_interval: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.poll_interval = poll_interval

    def health_check(self) -> tuple[bool, str]:
        """Check if the service is healthy."""
        try:
            data = self.get_json("/api/health")
            return True, data.get("status", "ok")
        except Exception as e:
            return False, str(e)

    def get_json(self, path: str, params: dict | None = None) -> dict:
        """GET a JSON endpoint."""
        url = f"{self.base_url}{path}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query}"
        req = Request(url, method="GET")
        req.add_header("Accept", "application/json")
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def post_json(self, path: str, data: dict) -> dict:
        """POST JSON to an endpoint."""
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode()
        req = Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def download_json(self, path: str, dest: Path, params: dict | None = None) -> Path:
        """Download a JSON response to a file."""
        url = f"{self.base_url}{path}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query}"
        req = Request(url, method="GET")
        req.add_header("Accept", "application/json")
        with urlopen(req, timeout=60) as resp:
            data = resp.read()
        dest.write_bytes(data)
        return dest

    def poll_until_complete(
        self,
        path: str,
        check_field: str = "status",
        target_values: list[str] | None = None,
        error_values: list[str] | None = None,
    ) -> dict:
        """Poll an endpoint until a field reaches a target value.

        Returns the final response data.
        Raises TimeoutError if the timeout is exceeded.
        Raises RuntimeError if an error status is reached.
        """
        if target_values is None:
            target_values = ["completed", "finished", "done"]
        if error_values is None:
            error_values = ["failed", "error"]

        start = time.time()
        while time.time() - start < self.timeout:
            data = self.get_json(path)
            status = data.get(check_field, "")
            if status in target_values:
                return data
            if status in error_values:
                raise RuntimeError(f"Service returned error status: {status}. Response: {data}")
            time.sleep(self.poll_interval)

        raise TimeoutError(f"Polling {path} timed out after {self.timeout}s (last status: {status})")


class CLIToolWrapper:
    """Base wrapper for CLI tools."""

    def __init__(self, binary_path: str):
        self.binary_path = str(Path(binary_path).expanduser())

    def check_installed(self) -> bool:
        """Check if the tool binary exists and is executable."""
        path = Path(self.binary_path)
        return path.exists() and path.is_file() and bool(path.stat().st_mode & 0o111)

    def version(self) -> str:
        """Get the tool version string."""
        rc, stdout, stderr = self.run(["--version"])
        if rc == 0:
            return stdout.strip()
        return f"unknown (exit {rc})"

    def run(
        self,
        args: list[str],
        cwd: str | Path | None = None,
        timeout: int | None = None,
        env: dict | None = None,
    ) -> tuple[int, str, str]:
        """Run the tool with arguments.

        Returns (returncode, stdout, stderr).
        """
        import os

        cmd = [self.binary_path] + args
        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout or 600,
            env=run_env,
        )
        return result.returncode, result.stdout, result.stderr

    def run_or_fail(
        self,
        args: list[str],
        cwd: str | Path | None = None,
        timeout: int | None = None,
        env: dict | None = None,
    ) -> str:
        """Run the tool and raise on non-zero exit."""
        rc, stdout, stderr = self.run(args, cwd=cwd, timeout=timeout, env=env)
        if rc != 0:
            raise RuntimeError(
                f"{self.binary_path} exited with code {rc}\nstdout: {stdout}\nstderr: {stderr}"
            )
        return stdout
