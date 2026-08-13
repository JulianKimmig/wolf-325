---
name: user-refinement-todos
description: Mark provisional content and actively ask the user to resolve every remaining refinement TODO.
apply: When Agents creates or encounters required working code, configuration, documentation, copy, generated text, data, or implementation decisions whose exact content is provisional and should be reviewed or refined by the user.
tags: implementation, documentation, todo, review
visibility: always
---

Do not create placeholders, dummy functions, inert stubs, or non-working filler
for behavior or text that the current task actually requires. Required content
must be complete enough for the implementation or artifact to work.

When the task requires concrete working content and the Agent can provide a usable
version, but the exact wording, value, domain choice, business rule, policy, or
project preference still needs user refinement, add a nearby `TODO: <message>`
comment.

Use the comment syntax native to the artifact, such as `# TODO: ...` in Python,
`// TODO: ...` in JavaScript or TypeScript, or `<!-- TODO: ... -->` in Markdown.
Place the TODO next to the provisional text, value, or implementation decision
it describes.

Write TODO messages as specific user-review actions, not vague reminders. The
message should explain what needs refinement or validation while keeping the
current implementation functional.

Do not use a TODO to hide incomplete behavior, bypass validation, or defer work
that the current task requires the Agent to finish. If uncertainty makes a safe,
working implementation impossible, ask the user instead of inventing filler.

Mention any remaining user-refinement TODOs in the final handoff so the user can
review them deliberately.

When one or more user-refinement TODOs remain, actively ask the user how the
next actionable TODO should be handled. Do not merely list TODOs and wait for
the user to notice them.

For each question:

- Ask one TODO at a time unless two decisions are inseparable.
- Provide three or four concise, mutually distinguishable choices that the user
  can select quickly.
- Put the recommended choice first and explain the main consequence or tradeoff
  of every choice in one short sentence.
- Explicitly welcome a free-text answer. A free-text answer may refine, combine,
  or replace the offered choices and takes precedence over them.
- Record the user's answer in the owning artifact, remove or update the resolved
  TODO, and then ask about the next remaining TODO.

Do not mark a TODO resolved merely because a recommended option exists. Continue
the refinement loop until no user-refinement TODOs remain or the user explicitly
asks to pause it.
