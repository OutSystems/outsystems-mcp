---
description: Send feedback about your OutSystems agent experience to the AI Platform team
argument-hint: [--cid=<studio-conversation-id>] <your feedback>
---

The user typed `/outsystems-feedback $ARGUMENTS`. They want to report something about the OutSystems agent experience (a bug, a thumbs-up / thumbs-down, a comment about a tool that misbehaved, etc.).

**Empty-message guard.** If `$ARGUMENTS` is empty or whitespace-only (including cases where the user typed only the `--cid=<id>` flag with no message), do NOT call `submit_feedback`. Reply to the user with: "`/outsystems-feedback` takes a message. Please type `/outsystems-feedback` followed by what you'd like to report."

**Optional `--cid=<id>` flag (Studio-conversation join).** Every submission already gets an automatic per-login-session correlation key (`odc.auth_session_id`, derived server-side from the JWT `sid` claim - happens with no user action). The `--cid=<value>` flag is a separate, narrower opt-in for cross-system correlation with Vishal's studio-agent traces: pass a Studio ConversationId to have the writer emit `mlflow.trace.session=<value>` so `mlflow.search_traces(filter="metadata.mlflow.trace.session=<value>")` returns both this feedback and the studio-agent trace for that specific Studio conversation. Use it only when the user actually wants that join - most submissions don't need it, the auth-session-id key already groups them per login.

If `$ARGUMENTS` starts with `--cid=<value>` (a token that runs to the next whitespace), split it off before redaction. The `<value>` is opaque (any string up to 256 bytes; the server does NOT validate it against a UUID pattern). Everything after the `--cid=<value>` token is the feedback message. Example: `/outsystems-feedback --cid=cid-abc-123 the diagram tool crashed on merge` -> message is `the diagram tool crashed on merge`, `ide_conversation_id` is `cid-abc-123`. If `--cid=` is absent, omit `ide_conversation_id` from the tool call - `odc.auth_session_id` still fires automatically.

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
- `ide_conversation_id`: only when the user passed a `--cid=<value>` flag (see above). Do NOT invent or guess an id; do NOT reuse `mentor_session_id` here. When present, the writer emits it as the SDK-canonical `mlflow.trace.session` metadata key so downstream `mlflow.search_traces(filter="metadata.mlflow.trace.session=X")` returns this feedback alongside the studio-agent trace for the same conversation. When absent, omit the argument entirely (do not pass an empty string - the server accepts it but downstream correlation stays orphan for this row).
- `mentor_session_id`: if there's a `mentor_session_id` you've been working with in this conversation, include it so the AI Platform team can co-locate the feedback with the relevant mentor trace. **Must be a UUID** (the server rejects non-UUID strings). Otherwise omit it and the server auto-falls-back to the user's most-recent mentor session on this pod. Server precedence: if both `ide_conversation_id` and `mentor_session_id` are passed, the IDE conversation id wins and `mentor_session_id` is silently dropped from the correlation dict (still recorded for our own debug queries). The server mints a placeholder trace either way, so the feedback still reaches the team.
- `agent_context`: OPTIONAL structured recap of what you were doing when the user typed `/outsystems-feedback`. Include it when the message clearly refers to a specific tool-call that misbehaved (e.g., "the deploy failed", "the publish returned garbage") - the recap makes downstream debug much faster. Shape: JSON string ≤2048 bytes with keys like `recent_tool_calls`, `app_key`, `env_key`. Redact secrets / PII (same rule as `rationale`). Skip when the feedback is general ("love the agent", "thumbs-up") - no tool-call context is relevant.

**Handle the response.**
- `status: "accepted"` → tell the user "Thanks, feedback sent to the AI Platform team."
- `status: "not_configured"` → the feedback writer isn't enabled on this stamp; tell the user "Feedback isn't configured on this OutSystems environment yet; I've noted what you said but it didn't reach the team."
- Any error (`data.category` of `ValidationError` / `UpstreamError` / `InternalError` / etc., per the SKILL.md error-categories rule) → tell the user "I couldn't send your feedback right now (<short reason from `data.category`); your message hasn't been delivered." Don't retry; this is user-initiated and the user can re-invoke `/outsystems-feedback`.

**Scope.** Don't volunteer this command. Don't proactively ask "would you like to submit feedback?". Only run this `/outsystems-feedback` flow when the user explicitly types it. `agent_observation` self-reports go through `submit_feedback` directly per the SKILL.md guidance, not through this command.
