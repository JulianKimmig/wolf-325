# Commit Message Validation Checklist

Use this checklist before returning a commit message or running `git commit`.

## Scope Checks

- The inspected diff matches the user-requested scope.
- Staged-only requests use only staged changes.
- Provided-file requests use only the provided files.
- All-changed requests include staged and unstaged changes as appropriate.
- Untracked files in scope were inspected before staging.
- Unrelated changes are split or the user is asked before combining.

## Conventional Commit Checks

- The first line matches `type[optional scope][optional !]: description`.
- The type is present.
- `feat` is used for features.
- `fix` is used for bug fixes.
- Other types are intentional and fit the change.
- Scope is a concise noun when present.
- `!` appears immediately before `:` when used.
- Description follows `: ` immediately.
- Description is specific, short, and describes what changed.
- Body starts one blank line after the description when present.
- Footers start one blank line after the body when present.
- Footer tokens use `-` instead of spaces, except `BREAKING CHANGE`.
- Breaking changes are marked with `!`, `BREAKING CHANGE:`, or both.
- `BREAKING CHANGE` is uppercase when used.
- `BREAKING-CHANGE` is accepted as synonymous but not preferred.

## Quality Checks

- The message is based on actual diff content, not guesses.
- The message does not mention files mechanically unless the file is the meaningful scope.
- The subject is not too broad for the selected changes.
- Body explains why or migration impact when the subject is not enough.
- Footers include issue references or review trailers only when known.
- No invented issue numbers, reviewers, SHAs, or breaking-change details.

## Commit Operation Checks

- The user asked to perform a commit.
- Selected files are staged according to the chosen scope.
- No unrelated files were staged.
- The commit message passed validation.
- If hooks fail, report the failure and stop.
