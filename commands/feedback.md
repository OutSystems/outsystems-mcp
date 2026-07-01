---
description: Send feedback about your OutSystems agent experience to the AI Platform team
argument-hint: <your feedback>
---

The user typed `/feedback $ARGUMENTS`. They want to report something about the OutSystems agent experience (a bug, a thumbs-up / thumbs-down, a comment about a tool that misbehaved, etc.).

**Empty-message guard.** If `$ARGUMENTS` is empty or whitespace-only, do NOT call `submit_feedback`. Reply to the user with: "`/feedback` takes a message. Please type `/feedback` followed by what you'd like to report."

**Redaction step (mandatory, unconditional).** Before constructing the tool call, scan `$ARGUMENTS` and replace each of these with `[redacted]`:
- Bearer tokens, JWTs, API keys, passwords, OAuth client secrets
- PII (email addresses, full names, phone numbers from any User entity)
- Code snippets and OML
- Full transcripts of multi-turn dialogue

After redacting, tell the user what you replaced. The redacted text is what you use below.

**Construct the call.** Call the OutSystems `submit_feedback` MCP tool with:
- `name`: `"user_feedback"`
- `value`: a one-word categorical tag (`"bug-report"`, `"feature-request"`, `"thumbs-up"`, `"thumbs-down"`) or a rating string (`"true"` / `"false"` / `"4"`). Pick the tag that best matches the user's message; default to `"bug-report"` if you can't tell. **Do NOT** put the user's prose into `value`; the AI Platform team groups feedback by `value` and free-form text breaks the slice. Cap 256 bytes (server rejects longer); single-word tags are well under.
- `rationale`: the full redacted user text goes here (cap 4096 bytes; truncate the tail and tell the user if it was longer).
- `mentor_session_id`: if there's a `mentor_session_id` you've been working with in this conversation, include it so the AI Platform team can co-locate the feedback with the relevant mentor trace. **Must be a UUID** (the server rejects non-UUID strings). Otherwise omit it; the server mints a placeholder trace either way, so the feedback still reaches the team.

**Handle the response.**
- `status: "accepted"` → tell the user "Thanks, feedback sent to the AI Platform team."
- `status: "not_configured"` → the feedback writer isn't enabled on this stamp; tell the user "Feedback isn't configured on this OutSystems environment yet; I've noted what you said but it didn't reach the team."
- Any error (`data.category` of `ValidationError` / `UpstreamError` / `InternalError` / etc., per the SKILL.md error-categories rule) → tell the user "I couldn't send your feedback right now (<short reason from `data.category`); your message hasn't been delivered." Don't retry; this is user-initiated and the user can re-invoke `/feedback`.

**Scope.** Don't volunteer this command. Don't proactively ask "would you like to submit feedback?". Only run this `/feedback` flow when the user explicitly types it. `agent_observation` self-reports go through `submit_feedback` directly per the SKILL.md guidance, not through this command.
