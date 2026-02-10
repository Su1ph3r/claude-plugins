"""BypassBurrito CLI wrapper — LLM-powered WAF bypass generator.

Wraps the `burrito` Go binary for WAF bypass payload generation.
Supports: Indago WAF-blocked import, multi-type attack generation.
"""

from pathlib import Path

from services.base import CLIToolWrapper


class BypassBurritoClient(CLIToolWrapper):
    """Wrapper for the BypassBurrito WAF bypass CLI."""

    def bypass(
        self,
        from_indago: str | None = None,
        url: str | None = None,
        param: str | None = None,
        method: str = "GET",
        attack_type: str = "all",
        output: str | None = None,
        format: str = "json",
        aggressive: bool = False,
        evolve: bool = False,
        extra_args: list[str] | None = None,
        cwd: str | Path | None = None,
        run_timeout: int = 600,
    ) -> tuple[int, str, str]:
        """Generate WAF bypass payloads.

        Either from_indago or (url + param) is required.
        """
        args = ["bypass"]

        if from_indago:
            args.extend(["--from-indago", str(from_indago)])
        else:
            if url:
                args.extend(["-u", url])
            if param:
                args.extend(["--param", param])
            args.extend(["-m", method])

        args.extend(["-t", attack_type])
        if output:
            args.extend(["-o", str(output)])
        args.extend(["-f", format])
        if aggressive:
            args.append("--aggressive")
        if evolve:
            args.append("--evolve")
        if extra_args:
            args.extend(extra_args)

        return self.run(args, cwd=cwd, timeout=run_timeout)

    def detect_waf(
        self,
        url: str,
        deep: bool = True,
        output: str | None = None,
        format: str = "json",
    ) -> tuple[int, str, str]:
        """Detect and fingerprint WAF on a target."""
        args = ["detect", "-u", url]
        if deep:
            args.append("--deep")
        if output:
            args.extend(["-o", str(output)])
        args.extend(["-f", format])
        return self.run(args, timeout=120)
