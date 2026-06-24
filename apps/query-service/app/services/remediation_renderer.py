from app.schemas.remediation import RemediationResult


def render_remediation(result: RemediationResult) -> str:
    sections = ["## Summary", result.summary]

    sections.extend(
        [
            "## Evidence",
            *[
                f"- {fact.statement} ({', '.join(fact.evidence_ids)})"
                for fact in result.observed_facts
            ],
        ]
    )

    if result.probable_causes:
        sections.extend(
            [
                "## Probable Causes",
                *[
                    (
                        f"- {cause.cause} (confidence {cause.confidence:.0%}; "
                        f"{', '.join(cause.evidence_ids)})"
                    )
                    for cause in result.probable_causes
                ],
            ]
        )

    sections.extend(
        [
            "## Diagnostic Actions",
            *[
                (
                    f"- {action.action}: {action.rationale} "
                    f"({', '.join(action.evidence_ids)})"
                )
                for action in result.diagnostic_actions
            ],
        ]
    )

    if result.remediation_steps:
        sections.extend(
            [
                "## Recommended Actions",
                *[
                    (
                        f"- {action.action}: {action.rationale} "
                        f"[risk: {action.risk}] "
                        f"({', '.join(action.evidence_ids)})"
                    )
                    for action in result.remediation_steps
                ],
            ]
        )

    if result.code_suggestion is not None:
        suggestion = result.code_suggestion
        sections.extend(
            [
                "## Code/Configuration Suggestion",
                suggestion.description,
                f"```{suggestion.language}\n{suggestion.code}\n```",
                "Evidence: " + ", ".join(suggestion.evidence_ids),
            ]
        )

    sections.extend(
        [
            "## Confidence and Limitations",
            f"Confidence: {result.confidence:.0%}",
            *[f"- {item}" for item in result.limitations],
        ]
    )

    return "\n\n".join(sections)
