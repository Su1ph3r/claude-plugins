"""Ariadne CLI wrapper — AI-powered attack path synthesizer.

Wraps the `ariadne` Python CLI for attack path synthesis from correlated findings.
Supports: playbook generation, credential sprawl, privilege escalation chaining.
"""

from pathlib import Path

from services.base import CLIToolWrapper


class AriadneClient(CLIToolWrapper):
    """Wrapper for the Ariadne attack path synthesizer CLI."""

    def analyze(
        self,
        input_path: str,
        output: str | None = None,
        targets: list[str] | None = None,
        playbook: bool = True,
        sprawl: bool = True,
        privesc: bool = True,
        format: str = "json",
        extra_args: list[str] | None = None,
        cwd: str | Path | None = None,
        run_timeout: int = 300,
    ) -> tuple[int, str, str]:
        """Synthesize attack paths from recon/correlation data.

        Args:
            input_path: Path to Vinculum ariadne-format export or recon directory.
            targets: Crown jewel targets to prioritize.
            playbook: Generate operator playbooks.
            sprawl: Enable credential sprawl analysis.
            privesc: Enable privilege escalation chaining.
        """
        args = ["analyze", str(input_path)]

        if output:
            args.extend(["-o", str(output)])
        if targets:
            for t in targets:
                args.extend(["-t", t])
        if playbook:
            args.append("-p")
        if sprawl:
            args.append("-s")
        if privesc:
            args.append("--privesc")
        args.extend(["-f", format])
        if extra_args:
            args.extend(extra_args)

        return self.run(args, cwd=cwd, timeout=run_timeout)

    def export_endpoints(
        self,
        input_path: str,
        output: str | None = None,
    ) -> tuple[int, str, str]:
        """Export discovered endpoints as Indago targets."""
        args = ["export-endpoints", str(input_path)]
        if output:
            args.extend(["-o", str(output)])
        args.extend(["-f", "indago"])
        return self.run(args, timeout=60)
