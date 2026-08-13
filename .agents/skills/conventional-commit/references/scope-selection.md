# Change Scope Selection

Select the change set before reading diffs or composing a message.

## Precedence

1. Explicit user scope.
2. Explicit staged/index request.
3. Staged files for commit requests when staged changes already exist and no broader scope was requested.
4. All changed files only when explicitly requested or clearly implied by the absence of staged changes.

## Staged Files

Use staged files when the user says:

- staged
- cached
- index
- commit staged
- commit what is staged
- make a message for the staged changes

Inspect with:

```text
git status --short
git diff --cached --stat
git diff --cached
```

Do not inspect unstaged diffs as part of the message except to warn that unrelated unstaged changes exist.

## Provided Files

Use only provided files when the user gives paths, pathspecs, or a file list.

Inspect with:

```text
git status --short -- <paths>
git diff -- <paths>
git diff --cached -- <paths>
```

If committing, stage only those paths. If provided files include untracked files, read them before staging.

## All Changed Files

Use all changed files when the user says:

- all changed files
- all changes
- everything
- whole working tree
- commit all

Inspect with:

```text
git status --short
git diff --stat
git diff
git diff --cached --stat
git diff --cached
```

If committing all changed files, stage modified, deleted, and untracked files only after inspecting enough context to write an accurate message.

## Ambiguity Rules

- If staged and unstaged changes both exist and the user simply says "commit", use staged files by default.
- If no files are staged and the user says "commit this" after a coding task, use the files changed by the task if known; otherwise inspect all changed files and confirm if scope is unclear.
- If the selected scope contains unrelated changes, recommend split commits.
- If the selected scope contains no changes, do not produce a fake message.

## Safety Rules

- Do not stage unrelated files.
- Do not modify files to make a commit message fit.
- Do not run destructive git commands.
- Do not bypass hooks with `--no-verify` unless the user explicitly asks.
- Do not use broad pathspecs when the user provided a narrow file list.
