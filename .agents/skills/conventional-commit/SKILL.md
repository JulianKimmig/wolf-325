---
name: conventional-commit
description: Create Conventional Commits 1.0.0 compliant commit messages and assist with git commits. Use automatically when the user asks for a commit message, asks to create or perform a commit, says to commit staged files, provides files to commit, asks to commit all changed files, asks to amend, rename, reword, squash, fix up, or otherwise change a git commit message, needs a squash or PR commit title, or asks whether a change should be feat, fix, chore, docs, test, refactor, perf, build, ci, style, or revert. The skill determines whether to use already staged files, an explicit file list, or all changed files based on the user's request and git state.
---

# Conventional Commit

## Overview

Create human-readable and machine-readable commit messages that follow Conventional Commits 1.0.0. Use the requested or inferred change scope, inspect the actual diff before writing the message, and commit only when the user asked for a commit operation.

## Trigger Rules

Use this skill whenever the user asks to create, amend, rename, reword, squash, fix up, or otherwise change a git commit message.

Trigger phrases include:

- "commit"
- "amend"
- "rename the last commit"
- "reword the commit"
- "change the commit message"
- "include this file in the last commit"
- "fixup"
- "squash"

This skill applies even when the user does not explicitly say "conventional commit".

## Required References

- Read [references/conventional-commits.md](references/conventional-commits.md) before composing a message if the exact structure, breaking-change rules, footers, or examples matter.
- Read [references/scope-selection.md](references/scope-selection.md) when choosing between staged files, provided files, and all changed files.
- Read [references/validation-checklist.md](references/validation-checklist.md) before finalizing a message or running `git commit`.

## Workflow

1. Determine whether the user wants only a commit message or wants a commit performed.
2. Determine the target change set:
   - Use already staged files when the user says staged, cached, index, commit what is staged, or when a commit is requested and staged changes already exist without an explicit broader scope.
   - Use only provided files when the user gives paths, globs, or a file list.
   - Use all changed files only when the user explicitly says all changes, all changed files, everything, whole working tree, or there are no staged files and the request clearly means current changes.
3. Inspect the target changes before composing the message. Use `git status --short`, `git diff --cached`, `git diff -- <paths>`, `git diff`, and file reads as appropriate for the selected scope.
4. If the selected scope mixes unrelated changes that need different commit intents, recommend splitting into multiple commits. If the user asked to commit anyway, ask before combining unrelated changes.
5. Choose the Conventional Commit type, optional scope, optional breaking marker, description, body, and footers from the inspected change.
6. Validate the message against [references/validation-checklist.md](references/validation-checklist.md).
7. If only a message was requested, return the message in a fenced code block and briefly state the inspected scope.
8. If a commit was requested, stage only the selected files when needed, then run `git commit` with the finalized message. Do not stage unrelated files. Report the commit result and final message.

## Message Construction

Use this shape:

```text
type[optional scope][optional !]: description

[optional body]

[optional footer(s)]
```

Required:

- A type followed by optional scope, optional `!`, and `: `.
- A short description immediately after `: `.
- `feat` for a new feature.
- `fix` for a bug fix.

Allowed common types:

- `feat`: new feature.
- `fix`: bug fix.
- `docs`: documentation-only change.
- `test`: test additions or corrections.
- `refactor`: code restructuring without feature or bug-fix intent.
- `perf`: performance improvement.
- `build`: build system or dependency packaging change.
- `ci`: CI configuration or workflow change.
- `style`: formatting or style-only change that does not affect behavior.
- `chore`: maintenance work that does not fit another type.
- `revert`: revert prior commit(s).

Use other types only when the repository convention clearly supports them.

## Scope Selection

Prefer a concise noun scope when it adds useful context, such as `api`, `auth`, `parser`, `ui`, `deps`, `ci`, or a package/module name. Omit scope when the change is broad or the scope would be vague.

## Breaking Changes

Mark breaking changes with either:

- `!` before the colon, such as `feat(api)!: remove legacy token format`.
- A footer beginning exactly with `BREAKING CHANGE: ` followed by the description.

Use both when clarity is helpful. `BREAKING-CHANGE` is synonymous as a footer token, but prefer `BREAKING CHANGE`.

## Bodies And Footers

Add a body when the reason, migration path, tradeoff, or implementation context matters. Start the body one blank line after the subject.

Add footers one blank line after the body. Footer tokens use hyphens instead of spaces, except `BREAKING CHANGE`. Examples:

```text
Reviewed-by: Z
Refs: #123
BREAKING CHANGE: environment variables now take precedence over config files
```

For reverts, prefer:

```text
revert: describe reverted change

Refs: <sha>
```

## Commit Operation Rules

- Never run `git commit` unless the user asked to commit.
- Never include unstaged changes when the selected scope is staged-only.
- Never stage all changes unless the selected scope is all changed files.
- When a file list is provided, stage and commit only those files.
- For untracked files in the selected scope, inspect them before staging.
- Preserve user changes outside the selected scope.
- If no changes exist in the selected scope, say so and do not invent a message.
- If repository hooks fail, report the failure and do not retry with bypass flags unless the user explicitly asks.

## Final Response

For message-only requests, include:

- Selected scope.
- Final commit message.
- Any split-commit recommendation if relevant.

For performed commits, include:

- Selected scope.
- Commit SHA or git's commit summary when available.
- Final commit message.
- Any hook/test failure details if the commit did not complete.
