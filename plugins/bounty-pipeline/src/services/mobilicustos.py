"""Mobilicustos service client — mobile application security analysis.

REST API client for the Mobilicustos Docker service.
Handles: scan creation, polling, finding export.
"""

import json
from pathlib import Path

from services.base import RESTServiceClient


class MobilicustosClient(RESTServiceClient):
    """Client for the Mobilicustos mobile security service."""

    def create_scan(self, app_id: str, scan_type: str = "full") -> dict:
        """Create a new mobile app scan.

        Args:
            app_id: The application ID to scan.
            scan_type: "full", "static", or "dynamic".

        Returns the created scan object including scan_id.
        """
        return self.post_json("/api/scans/", {
            "app_id": app_id,
            "scan_type": scan_type,
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
