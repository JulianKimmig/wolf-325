---
name: process-wait-brainstorming
description: Capture actionable future improvement candidates while waiting on long-running processes.
apply: When Codex starts or waits for a process that may take noticeable time, such as tests, builds, installs, servers, or other long-running commands.
tags: process, wait, tests, builds, installs, servers, commands
visibility: always
---

When waiting for a process that may take noticeable time, briefly use the idle time to identify possible future improvements based only on context already known from the active task.

Write a note only when there is a concrete, actionable improvement candidate for the project, workspace, process, codebase, product, or developer workflow. The note must name the improvement target and explain why changing it would make future work or outcomes better. It should be usable later as backlog material for prioritization or implementation.

Do not write notes that are merely progress updates, factual observations, intended next steps, implementation details, duplicates of the current task, generic facts, or trivial restatements. If no useful improvement candidate is apparent without extra investigation, write nothing.

Keep brainstorming short-lived. It must not block, delay, or distract from the active task, and it must not trigger extra file lookups, searches, inspection, or analysis solely to create a note.

Store qualifying notes in a single Markdown file at `.brainstorm/process-wait-brainstorm.md`. Append concise entries there instead of creating additional brainstorming files.
