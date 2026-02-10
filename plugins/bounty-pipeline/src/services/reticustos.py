"""Reticustos service client — network reconnaissance.

REST API client for the Reticustos Docker service.
Handles: target registration, scan execution, polling, endpoint export.
"""

from pathlib import Path

from services.base import RESTServiceClient


class ReticustosClient(RESTServiceClient):
    """Client for the Reticustos network recon service."""

    def register_target(self, target: str) -> dict:
        """Register a new target for scanning.

        Returns the created scan object including scan_id.
        """
        return self.post_json("/api/scans/", {"target": target})

    def start_scan(self, scan_id: str, profile: str = "standard") -> dict:
        """Start a scan with the given profile."""
        return self.post_json(f"/api/scans/{scan_id}/start", {"profile": profile})

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

    def export_endpoints(self, scan_id: str, output_path: Path) -> Path:
        """Export discovered endpoints for Indago consumption.

        Downloads the endpoint export JSON to output_path.
        """
        return self.download_json(
            "/api/exports/endpoints",
            output_path,
            params={"scan_id": scan_id},
        )

    def export_findings(self, scan_id: str, output_path: Path) -> Path:
        """Export full findings JSON for Vinculum consumption."""
        findings = self.get_findings(scan_id)
        import json
        output_path.write_text(json.dumps(findings, indent=2))
        return output_path
