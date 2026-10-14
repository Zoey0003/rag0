---
name: "RAG Debugging Workflow"
description: "Use when debugging or implementing a Python RAG feature, especially LangGraph routing, Milvus retrieval, document ingestion, embeddings, or runtime validation. Follow a focused investigation, make the smallest root-cause fix, and verify with the narrowest relevant check before widening scope."
---

# RAG Debugging Workflow

This skill captures the project workflow for debugging and validating changes in the Python RAG workspace. It is optimized for focused root-cause investigation and evidence-based verification.

## When to use
- debugging graph state transitions, node logic, retries, or routing
- fixing Markdown ingestion, metadata handling, or chunking behavior
- investigating dense/sparse retrieval, embedding configuration, or Milvus issues
- reviewing Python code changes in the RAG project before merge or handoff

## Workflow

1. Identify the smallest concrete entry point.
   - Start from the actual symptom, failing command, trace, or test.
   - Prefer the most local failing symbol or graph entry rather than broad project-wide inspection.

2. Read the owning implementation and one nearby caller or test.
   - Trace the behavior from the entry point through the relevant node, chain, retriever, or data layer.
   - Look for state contracts, configuration assumptions, and missing dependency checks.

3. State a falsifiable hypothesis.
   - Describe the likely root cause in one sentence before changing code.
   - Focus on the mechanism behind the bug, not just its visible symptom.

4. Make the smallest safe edit.
   - Keep the change local and minimal.
   - Preserve existing naming, import style, and module structure.
   - Do not invent APIs, dependency versions, or configuration values.

5. Validate with the narrowest relevant check.
   - Run the smallest available test, import check, compile check, or focused dry run.
   - Do not claim a fix without fresh evidence from the validation step.

6. Inspect the resulting diff and summarize the outcome.
   - Report the root cause and what changed.
   - Note any remaining external dependency limitation, such as missing Milvus, model credentials, or unavailable services.

## Decision points

- If the behavior is controlled by a single function or node, patch that local surface first.
- If the behavior crosses graph orchestration, verify the state contract and node transitions before changing business logic.
- If the issue involves ingestion or retrieval quality, inspect document metadata, chunking, and embedding assumptions before rewriting behavior.
- If the environment is missing external services, report the limitation clearly rather than guessing at the fix.
- If no test surface exists, prefer a narrow import/compile check or a controlled dry run over broad speculation.

## Quality criteria

A task is complete only when all of the following are true:
- The root cause is identified and linked to the fix.
- The patch is minimal and does not widen scope unnecessarily.
- Validation evidence was collected from the relevant command or check.
- Remaining risks or external prerequisites are described precisely.
- The final summary explains the changed behavior and the validation performed.

## Output format

Return a concise result with:
- Finding or change: the root cause and the actual change made.
- Validation: the exact command or check and its result.
- Risks or follow-up: only concrete remaining issues, such as missing credentials, unavailable services, or coverage gaps.

## Guardrails

- Do not hard-code secrets or credentials.
- Do not claim runtime success without running a relevant validation step.
- Do not broaden the codebase with refactors unrelated to the bug or feature.
- Preserve public module names and graph state keys unless the task explicitly requires a contract change.

## Example prompts

- "Diagnose why the LangGraph router is skipping the retrieval node in this RAG flow."
- "Fix the Markdown ingestion issue where document metadata is lost during indexing."
- "Trace the Milvus query mismatch and validate the retrieval path with the smallest relevant check."
- "Review this Python change for a state contract regression and report the exact validation evidence."
