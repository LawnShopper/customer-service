"""
Save triage results to local files.

Outputs both JSON (full detail) and CSV (easy to scan in a spreadsheet).
"""

import csv
import json
from pathlib import Path
from typing import Dict, Union

from agent.config import resolve_path
from agent.models import TriageBatch, TriageResult


def save_results(results: list, output_dir: Union[str, Path]) -> Dict[str, Path]:
    """
    Write triage results to JSON and CSV files.

    Returns the paths of the files that were written.
    """
    from agent.triage import count_needs_response, now_iso

    directory = resolve_path(str(output_dir))
    directory.mkdir(parents=True, exist_ok=True)

    batch = TriageBatch(
        processed_at=now_iso(),
        message_count=len(results),
        needs_response_count=count_needs_response(results),
        results=results,
    )

    json_path = directory / "triage_results.json"
    csv_path = directory / "triage_results.csv"

    # Also save a timestamped copy so each run is easy to find.
    stamp = batch.processed_at.replace(":", "-").replace("+", "_")[:19]
    stamped_csv = directory / f"triage_results_{stamp}.csv"
    stamped_json = directory / f"triage_results_{stamp}.json"

    json_path.write_text(
        batch.model_dump_json(indent=2),
        encoding="utf-8",
    )
    stamped_json.write_text(
        batch.model_dump_json(indent=2),
        encoding="utf-8",
    )

    fieldnames = [
        "message_id",
        "sender",
        "classification",
        "category",
        "urgency",
        "summary",
        "reasoning",
        "missing_info",
        "draft_reply",
        "recommended_human_action",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            row = result.model_dump()
            row["missing_info"] = "; ".join(row["missing_info"])
            writer.writerow(row)

    with stamped_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            row = result.model_dump()
            row["missing_info"] = "; ".join(row["missing_info"])
            writer.writerow(row)

    return {
        "json": json_path,
        "csv": csv_path,
        "stamped_csv": stamped_csv,
        "stamped_json": stamped_json,
    }
