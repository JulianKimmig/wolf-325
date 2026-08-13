---
name: repo-rule-search
description: Search local `.rules` metadata before work that may be governed by repository rules. Use when a task may involve code edits, config or hook changes, generated files, long-running commands, external tools, subagents, or when the user asks to find applicable rules by tags.
---

# Repo Rule Search

## Workflow

Use this skill's local query scripts instead of relying on all rule headers
being preloaded. Do not call scripts from other skills or from the hook bundle.

1. Build a Boolean tag expression from the task, files, tools, and intended
   commands. Use `AND`, `OR`, `NOT`, and parentheses.
2. Query reduced headers:

   ```bash
   python .agents/skills/repo-rule-search/scripts/query_rules.py --tags "tag AND other"
   ```

3. Review returned `name`, `description`, `apply`, `tags`, `visibility`, and
   path fields.
4. Read the full rule file for every returned rule that applies or remains
   uncertain.
5. Query again when new files, tools, commands, or subagent scopes are
   discovered.

Use `--include-manual` only when explicitly searching manual-only
`visibility: never` rules.

## Query Examples

```bash
python .agents/skills/repo-rule-search/scripts/query_rules.py --tags "codex AND config"
python .agents/skills/repo-rule-search/scripts/query_rules.py --tags "process AND wait"
python .agents/skills/repo-rule-search/scripts/query_rules.py --tags "(cli OR tui) AND codexmgr"
python .agents/skills/repo-rule-search/scripts/query_rules.py --tags "ui AND react AND NOT vite"
```

## Visibility

- `always`: appears in startup bootstrap context.
- `on_request`: discoverable through normal query.
- `never`: manual-only; returned only with `--include-manual`.

## Rule-Scout Subagent

For broad or ambiguous work, delegate a low-reasoning rule-scout subagent. Give
it:

- the planned task;
- likely tags/domains;
- known files or paths;
- intended tools or commands;
- whether manual-only rules may be included.

Ask it to run the same query command, return reduced headers and paths, provide
brief relevance reasons, and list full rule files the main agent should read.
The scout must not invent independent rule-selection semantics.
