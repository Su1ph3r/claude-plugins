"""Cepheus CLI wrapper — container escape scenario modeler.

Wraps the `cepheus` Python CLI for container posture analysis.
Supports: enumeration, escape path analysis, Nubicustos cloud context import.
"""

from pathlib import Path

from services.base import CLIToolWrapper


class CepheusClient(CLIToolWrapper):
    """Wrapper for the Cepheus container escape CLI."""

    def analyze(
        self,
        posture_file: str,
        from_nubicustos: str | None = None,
        output: str | None = None,
        format: str = "json",
        min_severity: str = "low",
        llm: bool = False,
        extra_args: list[str] | None = None,
        cwd: str | Path | None = None,
        run_timeout: int = 300,
    ) -> tuple[int, str, str]:
        """Analyze container posture for escape paths.

        Args:
            posture_file: Path to posture JSON from enumerator.
            from_nubicustos: Path to Nubicustos container export for cloud context.
        """
        args = ["analyze", str(posture_file)]

        if from_nubicustos:
            args.extend(["--from-nubicustos", str(from_nubicustos)])
        if output:
            args.extend(["-o", str(output)])
        args.extend(["-f", format])
        args.extend(["-s", min_severity])
        if llm:
            args.append("--llm")
        if extra_args:
            args.extend(extra_args)

        return self.run(args, cwd=cwd, timeout=run_timeout)

    def enumerate(
        self,
        container_id: str,
        runtime: str = "docker",
        output: str | None = None,
    ) -> tuple[int, str, str]:
        """Enumerate container posture.

        Args:
            container_id: Container ID or name.
            runtime: "docker" or "podman".
        """
        args = ["enumerate", "-c", container_id, "-r", runtime]
        if output:
            args.extend(["-o", str(output)])
        return self.run(args, timeout=120)
