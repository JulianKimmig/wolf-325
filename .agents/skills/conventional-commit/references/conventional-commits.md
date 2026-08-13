# Conventional Commits 1.0.0 Reference

Use these rules when composing or validating commit messages.

## Core Format

```text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

The commit contains structural elements that communicate intent:

- `fix`: patches a bug in the codebase and correlates with PATCH in Semantic Versioning.
- `feat`: introduces a new feature and correlates with MINOR in Semantic Versioning.
- `BREAKING CHANGE`: a footer `BREAKING CHANGE:`, or `!` after the type/scope, introduces a breaking API change and correlates with MAJOR in Semantic Versioning.
- Types other than `fix` and `feat` are allowed, such as `build`, `chore`, `ci`, `docs`, `style`, `refactor`, `perf`, `test`, and `revert`.
- Footers other than `BREAKING CHANGE` may be provided and follow a git-trailer-like convention.

## Formal Rules

- Commits must be prefixed with a type, followed by optional scope, optional `!`, and required terminal colon plus space.
- Use `feat` when a commit adds a new feature to an application or library.
- Use `fix` when a commit represents a bug fix for an application.
- A scope may be provided after a type. The scope must be a noun describing a section of the codebase surrounded by parentheses, such as `fix(parser):`.
- A description must immediately follow the colon and space after the type/scope prefix.
- A longer body may be provided after the short description and must begin one blank line after the description.
- A body is free-form and may contain any number of newline-separated paragraphs.
- One or more footers may be provided one blank line after the body.
- Each footer must consist of a word token followed by either `: ` or ` #`, then a string value.
- Footer tokens must use `-` instead of whitespace characters, such as `Acked-by`, except `BREAKING CHANGE`.
- Footer values may contain spaces and newlines. Parsing terminates when the next valid footer token/separator pair is observed.
- Breaking changes must be indicated in the type/scope prefix or as a footer.
- A breaking-change footer must use uppercase `BREAKING CHANGE: ` followed by a description.
- If breaking change is indicated in the prefix, use `!` immediately before `:`.
- If `!` is used, `BREAKING CHANGE:` may be omitted and the commit description describes the breaking change.
- Types other than `feat` and `fix` may be used.
- Type and footer units are not case-sensitive for implementors, except `BREAKING CHANGE`, which must be uppercase.
- `BREAKING-CHANGE` is synonymous with `BREAKING CHANGE` as a footer token.

## SemVer Meaning

- `fix` implies PATCH.
- `feat` implies MINOR.
- Any commit with `!` or `BREAKING CHANGE:` implies MAJOR.
- Other types have no implicit SemVer effect unless they include a breaking change.

## Common Type Selection

- `feat`: user-visible or API capability added.
- `fix`: defect corrected.
- `docs`: documentation-only update.
- `test`: tests added, updated, or corrected.
- `refactor`: internal restructuring without feature or bug-fix intent.
- `perf`: performance improvement.
- `style`: formatting or style-only change with no behavior impact.
- `build`: build system, packaging, or dependency setup.
- `ci`: CI workflow or pipeline configuration.
- `chore`: maintenance that does not fit a more specific type.
- `revert`: revert previous commit(s).

When a change fits multiple types, prefer splitting into multiple commits when possible.

## Examples

```text
feat: allow provided config object to extend other configs

BREAKING CHANGE: `extends` key in config file is now used for extending other config files
```

```text
feat!: send an email to the customer when a product is shipped
```

```text
feat(api)!: send an email to the customer when a product is shipped
```

```text
docs: correct spelling of CHANGELOG
```

```text
feat(lang): add Polish language
```

```text
fix: prevent racing of requests

Introduce a request id and a reference to latest request. Dismiss
incoming responses other than from latest request.

Remove timeouts which were used to mitigate the racing issue but are
obsolete now.

Reviewed-by: Z
Refs: #123
```

```text
revert: let us never again speak of the reverted change

Refs: 676104e, a215868
```
