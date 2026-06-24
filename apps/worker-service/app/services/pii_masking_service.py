from __future__ import annotations

from threading import Lock
from typing import Any

import torch
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizerBase,
)

from app.core.config import settings
from app.schemas.pii import PiiDetection


class PiiMaskingService:
    def __init__(self) -> None:
        self._tokenizer: (
            PreTrainedTokenizerBase | None
        ) = None
        self._model: PreTrainedModel | None = None
        self._device = torch.device(
            settings.pii_device
        )
        self._load_lock = Lock()

    def mask_text(self, text: str) -> str:
        if (
            not settings.pii_masking_enabled
            or not text
        ):
            return text

        detections = self.detect(text)

        masked = text

        for detection in reversed(detections):
            replacement = (
                f"[REDACTED_{detection.entity_type}]"
            )

            masked = (
                masked[:detection.start]
                + replacement
                + masked[detection.end:]
            )

        return masked

    def detect(
        self,
        text: str,
    ) -> list[PiiDetection]:
        if not text:
            return []

        self._ensure_model()

        assert self._tokenizer is not None
        assert self._model is not None

        encoded = self._tokenizer(
            text,
            return_tensors="pt",
            return_offsets_mapping=True,
            return_overflowing_tokens=True,
            truncation=True,
            max_length=settings.pii_max_tokens,
            stride=settings.pii_stride,
            padding="max_length",
        )

        offsets = encoded.pop("offset_mapping")
        encoded.pop(
            "overflow_to_sample_mapping",
            None,
        )

        detections: list[PiiDetection] = []

        window_count = encoded["input_ids"].shape[0]

        with torch.inference_mode():
            for window_index in range(window_count):
                model_inputs = {
                    key: value[
                        window_index:window_index + 1
                    ].to(self._device)
                    for key, value in encoded.items()
                    if key
                    in self._tokenizer.model_input_names
                }

                output = self._model(**model_inputs)

                probabilities = torch.softmax(
                    output.logits[0],
                    dim=-1,
                )

                scores, label_ids = torch.max(
                    probabilities,
                    dim=-1,
                )

                window_offsets = offsets[
                    window_index
                ]

                for token_index, label_id in enumerate(
                    label_ids.tolist()
                ):
                    start, end = (
                        window_offsets[token_index].tolist()
                    )

                    if start == end:
                        continue

                    label = self._model.config.id2label[
                        label_id
                    ]

                    entity_type = (
                        self._normalize_label(label)
                    )

                    if entity_type == "O":
                        continue

                    score = float(
                        scores[token_index].item()
                    )

                    detections.append(
                        PiiDetection(
                            entity_type=entity_type,
                            start=start,
                            end=end,
                            score=score,
                        )
                    )

        detections = self._merge_tokens(
            detections
        )

        detections = [
            detection
            for detection in detections
            if detection.score
            >= settings.pii_score_threshold
        ]

        return self._resolve_overlaps(
            detections
        )

    def mask_mapping(
        self,
        value: dict[str, Any],
    ) -> dict[str, Any]:
        if not settings.pii_masking_enabled:
            return value

        return {
            key: self._mask_value(item)
            for key, item in value.items()
        }

    def mask_mappings(
        self,
        values: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [self.mask_mapping(value) for value in values]

    def mask_error(
        self,
        error: Exception,
    ) -> str:
        return self.mask_text(str(error))[:2000]

    def _mask_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.mask_text(value)

        if isinstance(value, dict):
            return self.mask_mapping(value)

        if isinstance(value, list):
            return [
                self._mask_value(item)
                for item in value
            ]

        return value

    def _ensure_model(self) -> None:
        if (
            self._tokenizer is not None
            and self._model is not None
        ):
            return

        with self._load_lock:
            if (
                self._tokenizer is not None
                and self._model is not None
            ):
                return

            self._tokenizer = (
                AutoTokenizer.from_pretrained(
                    settings.pii_model_name
                )
            )

            self._model = (
                AutoModelForTokenClassification
                .from_pretrained(
                    settings.pii_model_name
                )
            )

            self._model.to(self._device)
            self._model.eval()

    def _normalize_label(
        self,
        label: str,
    ) -> str:
        normalized = label.upper()

        if normalized[:2] in {
            "B-",
            "I-",
            "B_",
            "I_",
        }:
            normalized = normalized[2:]

        return normalized.replace("-", "_")

    def _merge_tokens(
        self,
        detections: list[PiiDetection],
    ) -> list[PiiDetection]:
        if not detections:
            return []

        ordered = sorted(
            detections,
            key=lambda item: (
                item.start,
                item.end,
                -item.score,
            ),
        )

        merged: list[PiiDetection] = []

        for detection in ordered:
            if not merged:
                merged.append(detection)
                continue

            previous = merged[-1]

            same_entity = (
                previous.entity_type
                == detection.entity_type
            )

            touches_previous = (
                detection.start
                <= previous.end + 1
            )

            if same_entity and touches_previous:
                merged[-1] = PiiDetection(
                    entity_type=previous.entity_type,
                    start=min(
                        previous.start,
                        detection.start,
                    ),
                    end=max(
                        previous.end,
                        detection.end,
                    ),
                    score=max(
                        previous.score,
                        detection.score,
                    ),
                )
                continue

            merged.append(detection)

        return merged

    def _resolve_overlaps(
        self,
        detections: list[PiiDetection],
    ) -> list[PiiDetection]:
        selected: list[PiiDetection] = []

        candidates = sorted(
            detections,
            key=lambda item: (
                -item.score,
                -(item.end - item.start),
            ),
        )

        for candidate in candidates:
            overlaps = any(
                candidate.start < existing.end
                and candidate.end > existing.start
                for existing in selected
            )

            if not overlaps:
                selected.append(candidate)

        return sorted(
            selected,
            key=lambda item: item.start,
        )


pii_masking_service = PiiMaskingService()
