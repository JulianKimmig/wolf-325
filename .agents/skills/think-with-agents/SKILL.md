---
name: think-with-agents
description: Structured multi-agent thinking workflow for explicit use before answering a new user task. Use when the user invokes $think-with-agents or directly asks Codex to first create a .thoughts folder, collect perspectives with subagents, ask clarifying questions, run multiple reasoning agents, and summarize the findings into reusable Markdown artifacts before giving the final answer.
---

# Think With Agents

## Overview

Use this skill to defer the final answer until a structured thought workspace has been created, explored by subagents, clarified with the user, and summarized. Treat the Markdown files as durable working memory: append useful information as soon as it is available.

## Required Artifacts

Create all artifacts under the current working directory:

```text
.thoughts/<task-title>/
|-- perspectives.md
|-- clarification.md
|-- summary.md
`-- results/
    |-- agent-1.md
    |-- agent-2.md
    `-- ...
```

Start the workspace with:

```bash
python3 <skill-dir>/scripts/init_thought_session.py "<task title>" --base-dir "$PWD"
```

Use a concise title that captures the task, then use the script output as the thought folder path. Never overwrite an existing thought folder.

Every Markdown file must include and maintain a `## Chain-of-Thought Summary` section. This section should contain safe, reusable reasoning notes: rationale summaries, assumptions, explored alternatives, tradeoffs, temporary hypotheses, discarded paths, and decision reasons. Do not expose private hidden deliberation verbatim.

## Workflow

1. Create the thought workspace before answering the task.
2. Append the original task, task title, timestamp, and any immediate constraints to `perspectives.md`.
3. Spawn one perspective subagent with the highest reasoning level available for the current subagent tool (for example `reasoning_effort: "xhigh"` when supported). Its only job is to ultrathink about the task, identify missing aspects, contradictions, risks, assumptions, stakeholder perspectives, and different solution paths. It must not solve the task.
4. Instruct the perspective subagent to analyze in two explicit passes and reflect both in detail in `perspectives.md`:
   - **General Perspective**: reason about the task from a domain-general, repository-independent viewpoint first.
   - **Local Resource Perspective**: then inspect and reason from the current working directory, local files, existing code, docs, tests, and constraints.
   It must append findings continuously and include a dedicated `## Chain-of-Thought Summary` update with safe reasoning notes.
5. Read `perspectives.md`, then ask the user clear clarification questions when the file reveals contradictions, missing requirements, or dramatically different paths. Ask only questions that can materially change the answer or implementation.
6. Append each clarification question and user answer to `clarification.md` as soon as it arrives, including updated assumptions in `## Chain-of-Thought Summary`.
7. Ask the user how many reasoning agents should work on the task. Offer reasonable proposals based on task complexity, such as:
   - `1 agent` for small, narrow, low-risk tasks
   - `2-3 agents` for normal tasks with meaningful tradeoffs
   - `4-5 agents` for broad, ambiguous, high-risk, or strategic tasks
8. Spawn the selected number of reasoning subagents with high reasoning level (for example `reasoning_effort: "high"` when supported). Give each agent the original task, `perspectives.md`, and `clarification.md`. Do not make their tasks completely separate. Give every reasoning agent a shared core brief covering at least 50% of the same questions, acceptance criteria, risks, and recommendation surface, then add a secondary emphasis or angle when useful. The goal is overlapping independent perspectives from different agent identities, not a set of disjoint subtasks.
9. Instruct each reasoning subagent to append continuously to its own file in `results/agent-<n>.md`. Each result file must include:
   - source task context
   - assumptions and constraints
   - explored options
   - findings and proposed answer or solution
   - `## Chain-of-Thought Summary` with safe reasoning notes
   - unresolved questions and risks
10. Read `perspectives.md`, `clarification.md`, and all result files, then synthesize the final answer into `summary.md` as a durable handoff artifact. Do not merely compress each agent result into a short bullet or organize the main body by agent identity. Organize the synthesis by topic, decision area, option, risk area, implementation concern, or other task-relevant structure. Merge overlapping findings into integrated conclusions, preserve material unique contributions, surface contradictions explicitly, resolve them when the available evidence supports a resolution, and mark unresolved decisions with the information needed to resolve them.
11. Give the user a detailed summary of the findings and thoughts, referencing the thought folder path.

## Subagent Prompt Requirements

Tell subagents:

- Write to the assigned Markdown file early and append updates whenever new information arrives.
- Preserve temporary findings, uncertainty, rejected options, and intermediate conclusions when useful for later reuse.
- Keep the `## Chain-of-Thought Summary` section current with safe reasoning summaries, not hidden reasoning transcripts.
- Do not delete or rewrite prior notes except to add a clearly labeled correction.
- Do not answer outside the assigned artifact unless asked for a final handoff.

For the initial perspective subagent, always include:

- Use the maximum supported reasoning effort for the current tool.
- Ultrathink about the task before narrowing.
- Write separate detailed sections for `## General Perspective` and `## Local Resource Perspective` in `perspectives.md`.
- In `## General Perspective`, analyze the problem without assuming the current repository structure, available libraries, or local implementation details.
- In `## Local Resource Perspective`, inspect relevant files and adapt the general findings to the current working directory, codebase, tests, docs, and constraints.

For reasoning subagents, always include:

- Use high reasoning effort.
- Work from a shared core brief that overlaps with the other reasoning agents by at least 50%.
- Cover the same central task, constraints, acceptance criteria, and main risks as the other reasoning agents.
- Add only a secondary emphasis or angle to create perspective diversity.
- Avoid assigning fully disjoint responsibilities that prevent meaningful comparison between agent outputs.

## Clarification Handling

Ask clarification questions after the perspective pass unless there are no material ambiguities. If clarification is not needed, append that decision and rationale to `clarification.md`.

When the user answers, append:

- the exact question asked
- the user answer
- any changed assumptions
- any newly excluded paths
- any impact on agent count or agent assignments

## Final Summary

Write `summary.md` as a comprehensive cross-agent synthesis. It must include:

- the original task, final clarified task, and important constraints
- the clarification journey, including decisions, excluded paths, and changed assumptions
- integrated findings from `perspectives.md` and all reasoning agents, organized by topic, decision area, option, risk, or implementation concern rather than by agent identity
- merged conclusions where agents agree or overlap
- material unique contributions from individual sources when they add value
- contradictions, disagreements, and incompatible assumptions, with a resolution when the available evidence supports one
- unresolved decisions or questions, including what information would resolve them
- evaluated options and tradeoffs
- implementation-relevant recommendations or final strategy
- validation needs, follow-up checks, and remaining risks
- brief source notes or a source map showing which artifacts contributed to major conclusions
- `## Chain-of-Thought Summary` containing safe reasoning notes that explain the synthesis without exposing private hidden deliberation verbatim

Longer and richer source artifacts should produce a proportionally richer `summary.md`. The summary may be concise where inputs are simple, but it must preserve substantive assumptions, evidence, options, tradeoffs, risks, disagreements, and implementation-relevant conclusions from the available source material.

The final user response may be shorter than `summary.md`, but should summarize the same conclusions and mention where the artifacts were written.
