"""Indago CLI wrapper — AI-powered API security fuzzer.

Wraps the `indago` Go binary for API scanning.
Supports: spec-based scanning, Reticustos target import, WAF-blocked export.
"""

from pathlib import Path

from services.base import CLIToolWrapper


class IndagoClient(CLIToolWrapper):
    """Wrapper for the Indago API fuzzer CLI."""

    def scan(
        self,
        spec: str | None = None,
        targets_from: str | None = None,
        output: str | None = None,
        format: str = "json",
        export_waf_blocked: str | None = None,
        concurrency: int | None = None,
        rate_limit: int | None = None,
        timeout: str | None = None,
        extra_args: list[str] | None = None,
        cwd: str | Path | None = None,
        run_timeout: int = 600,
    ) -> tuple[int, str, str]:
        """Run an Indago API security scan.

        One of spec or targets_from is required.
        """
        args = ["scan"]

        if spec:
            args.extend(["--spec", str(spec)])
        if targets_from:
            args.extend(["--targets-from", str(targets_from)])
        if output:
            args.extend(["-o", str(output)])
        args.extend(["-f", format])
        if export_waf_blocked:
            args.extend(["--export-waf-blocked", str(export_waf_blocked)])
        if concurrency:
            args.extend(["--concurrency", str(concurrency)])
        if rate_limit:
            args.extend(["--rate-limit", str(rate_limit)])
        if timeout:
            args.extend(["--timeout", timeout])
        if extra_args:
            args.extend(extra_args)

        return self.run(args, cwd=cwd, timeout=run_timeout)

    def dry_run(
        self,
        spec: str | None = None,
        targets_from: str | None = None,
    ) -> tuple[int, str, str]:
        """Run Indago in dry-run mode to show what would be tested."""
        args = ["scan", "--dry-run"]
        if spec:
            args.extend(["--spec", str(spec)])
        if targets_from:
            args.extend(["--targets-from", str(targets_from)])
        return self.run(args, timeout=30)
