"""Vinculum CLI wrapper — security finding correlation engine.

Wraps the `vinculum` Python CLI for multi-tool finding correlation.
Supports: ingesting reports from all pipeline tools, Ariadne-format export.
"""

from pathlib import Path

from services.base import CLIToolWrapper


class VinculumClient(CLIToolWrapper):
    """Wrapper for the Vinculum correlation engine CLI."""

    def ingest(
        self,
        files: list[str],
        format: str = "ariadne",
        output: str | None = None,
        min_severity: str = "info",
        include_raw: bool = False,
        extra_args: list[str] | None = None,
        cwd: str | Path | None = None,
        run_timeout: int = 120,
    ) -> tuple[int, str, str]:
        """Ingest and correlate findings from multiple tool reports.

        Args:
            files: List of report file paths to ingest.
            format: Output format — "json", "console", "sarif", or "ariadne".
            output: Output file path (required for json/sarif/ariadne).
            min_severity: Minimum severity filter.
            include_raw: Include raw tool data in output.
        """
        args = ["ingest"] + [str(f) for f in files]
        args.extend(["-f", format])
        if output:
            args.extend(["-o", str(output)])
        args.extend(["--min-severity", min_severity])
        if include_raw:
            args.append("--include-raw")
        if extra_args:
            args.extend(extra_args)

        return self.run(args, cwd=cwd, timeout=run_timeout)

    def stats(self, results_file: str) -> tuple[int, str, str]:
        """Show statistics from a correlation results file."""
        return self.run(["stats", str(results_file)], timeout=30)
