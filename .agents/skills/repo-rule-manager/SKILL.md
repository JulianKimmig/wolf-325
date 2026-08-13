---
name: repo-rule-manager
description: Create or update durable repository rules in local `.rules/**/*.md` files. Use when the user asks to turn guidance into a rule or repo convention, including wording like "make this a rule", "add a rule", "new rule", "always make sure", "from now on", "never do this again", "remember this for this repo", "this should always happen", or when the request is a general rule for the current repository. Also use when the requested rule explicitly changes, replaces, broadens, narrows, or closely overlaps an existing rule.
---

# Repo Rule Manager

## Workflow

Create or update a local Markdown rule under `.rules/`. Rules are durable
repository guidance, not task notes.

1. Identify the durable requirement from the user's wording. Keep the rule
   general enough to apply to future work in this repository.
2. Inspect `.rules/` recursively before editing. Read all rule headers first.
   If a header is close to the new requirement, read that rule body too.
3. Update an existing rule instead of creating a duplicate when the user
   explicitly asks to change it, or when the requirement overlaps an existing
   rule and they can be consideret one.
4. Create a new rule only when no existing rule is a reasonable owner.

## Rule Format

Each rule file must be a Markdown file under `.rules/` and use this exact
shape:

```md
---
name: short-hyphen-name
description: Short description of the rule.
apply: When Codex should apply this rule.
---

Longer rule body.
```

Use lowercase hyphen-case for `name` and the filename. Prefer the filename
`.rules/<name>.md` for general rules, or `.rules/<topic>/<name>.md` when a
topic folder such as `.rules/react/` makes ownership easier to scan. Keep names
short and stable.

## Writing Rules

- Write `description` as a concise summary of the rule.
- Write `apply` as trigger guidance: tasks, wording, file types, workflows, or
  conditions where the rule matters.
- Write the body in imperative language with enough detail to apply the rule
  without re-reading the original conversation.
- Avoid one-off task details, timestamps, current branch names, or references to
  the specific correction unless they are part of the general rule.
- Do not add default fallbacks or vague guidance. If the rule cannot be stated
  clearly, ask one concise clarification question.

## Updating Existing Rules

When updating a close existing rule:

- Preserve the frontmatter format.
- Change `name` only if the old name no longer describes the rule.
- Update `description` and `apply` when the trigger conditions changed.
- Merge the new requirement into the body without weakening existing durable
  guidance unless the user explicitly asked for that change.

## Validation

After writing or updating a rule:

1. Confirm every rule file under `.rules/` except files named `overview.md`,
   `index.md`, and `README.md` has `name`, `description`, and `apply`.
2. Run the local rule hook when available:

   ```bash
   printf '{"cwd":"%s","hook_event_name":"SessionStart"}' "$PWD" \
     | python3 .codex/hooks/repo-rules/rules_context.py
   ```

3. Fix malformed rules that you touched. If unrelated malformed rules already
   exist, report them without changing them unless the user asked for cleanup.
