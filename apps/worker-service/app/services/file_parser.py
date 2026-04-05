from __future__ import annotations

import csv
import io
import json
from pathlib import Path


class FileParser:
    async def extract_text(self, file_name: str, file_bytes: bytes) -> str:
        suffix = Path(file_name).suffix.lower()

        if suffix in {".txt", ".log"}:
            return self._parse_text(file_bytes)

        if suffix == ".json":
            return self._parse_json(file_bytes)

        if suffix == ".csv":
            return self._parse_csv(file_bytes)

        raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")

    def _parse_text(self, file_bytes: bytes) -> str:
        return file_bytes.decode("utf-8", errors="ignore").strip()

    def _parse_json(self, file_bytes: bytes) -> str:
        data = json.loads(file_bytes.decode("utf-8", errors="ignore"))
        return json.dumps(data, ensure_ascii=True, indent=2)

    def _parse_csv(self, file_bytes: bytes) -> str:
        text = file_bytes.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = [" | ".join(row) for row in reader]
        return "\n".join(rows).strip()


file_parser = FileParser()
