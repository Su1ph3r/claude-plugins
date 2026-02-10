"""Nubicustos service client — cloud security audit.

REST API client for the Nubicustos Docker service.
Handles: scan creation, polling, finding export, container export for Cepheus.
"""

import json
from pathlib import Path

from services.base import RESTServiceClient


class NubicustosClient(RESTServiceClient):
    """Client for the Nubicustos cloud security service."""

    def create_scan(self, target: str, profile: str = "comprehensive") -> dict:
        """Create a new cloud security scan.

        Args:
            target: Cloud target identifier (AWS account, Azure sub, etc.).
            profile: Scan profile — "quick", "standard", or "comprehensive".

        Returns the created scan object including scan_id.
        """
        return self.post_json("/api/scans/", {
            "target": target,
            "profile": profile,
        })

    def poll_scan(self, scan_id: str) -> dict:
        """Poll until the scan completes. Returns final scan data."""
        return self.poll_until_complete(
            f"/api/scans/{scan_id}",
            check_field="status",
            target_values=["completed"],
            error_values=["failed", "error", "cancelled"],
        )

    def get_findings(self, scan_id: str) -> dict:
        """Get scan findings."""
        return self.get_json(f"/api/scans/{scan_id}/findings")

    def export_findings(self, scan_id: str, output_path: Path) -> Path:
        """Export findings JSON for Vinculum consumption."""
        findings = self.get_findings(scan_id)
        output_path.write_text(json.dumps(findings, indent=2))
        return output_path

    def export_containers(self, scan_id: str, output_path: Path) -> Path:
        """Export container inventory for Cepheus consumption.

        Downloads the container export JSON (export_source="nubicustos").
        """
        return self.download_json(
            "/api/exports/containers",
            output_path,
            params={"scan_id": scan_id},
        )
