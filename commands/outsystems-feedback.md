---
description: Send feedback about your OutSystems agent experience to the AI Platform team
argument-hint: [--cid=<studio-conversation-id>] [<message>] (leave empty for guided form)
---

The user typed `/outsystems-feedback $ARGUMENTS`. They want to report something about the OutSystems agent experience (a bug, a thumbs-up / thumbs-down, a comment about a tool that misbehaved, etc.).

## Two modes

Decide the mode from `$ARGUMENTS`:

- **Direct mode** -- `$ARGUMENTS` is non-empty and contains at least one non-whitespace character AFTER stripping any leading `--cid=<value>` token. The message body is whatever is left. Skip the guided-form steps and go straight to redaction + tool call.
- **Guided-form mode** -- `$ARGUMENTS` is empty, whitespace-only, OR consists only of a `--cid=<value>` token with no following message. Do NOT reply with an error. Drive the guided form below so the user picks values instead of typing them. This is the closest thing plugins have to Claude Code's built-in `/feedback` modal.

## Guided-form mode

Run these steps IN ORDER. Do not batch them into one `AskUserQuestion` call -- the two picker steps need to happen in sequence so the user's category choice is visible before they type the message.

**Step 1 -- category picker.** Call `AskUserQuestion` exactly once:

- `question`: "What kind of feedback would you like to send?"
- `header`: "Category"
- `multiSelect`: false
- `options` (in this order):
  - `label`: "Thumbs up" -- `description`: "Something worked well or is delightful."
  - `label`: "Thumbs down" -- `description`: "Something felt off but is not a full bug (mentor felt slow, output felt weird, etc.)."
  - `label`: "Bug report" -- `description`: "Something is broken and should not be."
  - `label`: "Feature request" -- `description`: "You would like the OutSystems agent to do something it does not currently do."

Map the user's pick to the `value` argument of `submit_feedback`:

- "Thumbs up" -> `"thumbs-up"`
- "Thumbs down" -> `"thumbs-down"`
- "Bug report" -> `"bug-report"`
- "Feature request" -> `"feature-request"`
- Any custom / "Other" free-text answer the user typed instead of picking -> default `value` to `"bug-report"` and include the user's free-text at the top of the message body.

**Step 2 -- free-text message.** After the pick lands, reply to the user in a single conversational turn:

> "Got it, <category>. What is the message you would like to include? (Skip this if the category above already says enough -- just reply 'none' or 'skip'.)"

Wait for the user's next message. Treat that message as the raw feedback body (subject to the redaction step below). If the user replies "none" / "skip" / an empty line, use an empty rationale.

**Step 3 -- optional Studio ConvId (skip when the user already passed `--cid=<value>` inline).** Call `AskUserQuestion` again:

- `question`: "Attach a Studio conversation id? Optional -- only if you want this feedback correlated with a specific studio-agent trace."
- `header`: "Attach ConvId"
- `multiSelect`: false
- `options` (in this order):
  - `label`: "Skip (Recommended)" -- `description`: "Do not attach a Studio ConversationId. The server still auto-emits `odc.auth_session_id` for per-login grouping -- most submissions do not need the ConvId."
  - `label`: "I will provide one" -- `description`: "Ask me for the Studio ConversationId. Use this only when you want to correlate with a specific studio-agent trace."

If the user picks "I will provide one", reply "Paste the Studio ConversationId:" and wait for their next message. Use that value as `ide_conversation_id`. If they pick "Skip", omit `ide_conversation_id`.

Then proceed to the redaction step below with the values collected across steps 1-3.

## Direct-mode parsing (leading `--cid=` flag)

Applies to direct mode only (guided-form mode collects the ConvId via Step 3 instead).

**Optional `--cid=<id>` flag (Studio-conversation join).** Every submission already gets an automatic per-login-session correlation key (`odc.auth_session_id`, derived server-side from the JWT `sid` claim -- happens with no user action). The `--cid=<value>` flag is a separate, narrower opt-in for cross-system correlation with Vishal's studio-agent traces: pass a Studio ConversationId to have the writer emit `mlflow.trace.session=<value>` so `mlflow.search_traces(filter="metadata.mlflow.trace.session=<value>")` returns both this feedback and the studio-agent trace for that specific Studio conversation. Use it only when the user actually wants that join -- most submissions do not need it, the auth-session-id key already groups them per login.

If `$ARGUMENTS` starts with `--cid=<value>` (a token that runs to the next whitespace), split it off before redaction. The `<value>` is opaque (any string up to 256 bytes; the server does NOT validate it against a UUID pattern). Everything after the `--cid=<value>` token is the feedback message. Example: `/outsystems-feedback --cid=cid-abc-123 the diagram tool crashed on merge` -> message is `the diagram tool crashed on merge`, `ide_conversation_id` is `cid-abc-123`. If `--cid=` is absent, omit `ide_conversation_id` from the tool call -- `odc.auth_session_id` still fires automatically.

## Redaction step (mandatory, unconditional)

Applies to both modes. Before constructing the tool call, scan the message body (from direct-mode args or guided-form Step 2) and replace each of these with `[redacted]`:
- Bearer tokens, JWTs, API keys, passwords, OAuth client secrets
- PII (email addresses, full names, phone numbers from any User entity)
- Code snippets and OML
- Full transcripts of multi-turn dialogue

After redacting, tell the user what you replaced. The redacted text is what you use below.

## Construct the call

Call the OutSystems `submit_feedback` MCP tool with:

- `name`: `"user_feedback"` -- always for this command. `agent_observation` self-reports go through `submit_feedback` directly per the SKILL.md guidance, not through this command.
- `value`: a one-word categorical tag (`"bug-report"`, `"feature-request"`, `"thumbs-up"`, `"thumbs-down"`) or a rating string (`"true"` / `"false"` / `"4"`). In guided-form mode, this comes from Step 1's pick (the mapping is fixed). In direct mode, pick the tag that best matches the user's message; default to `"bug-report"` if you cannot tell. **Do NOT** put the user's prose into `value`; the AI Platform team groups feedback by `value` and free-form text breaks the slice. Cap 256 bytes (server rejects longer); single-word tags are well under.
- `rationale`: the full redacted message body (cap 4096 bytes; truncate the tail and tell the user if it was longer). If the guided-form user replied "skip" / "none" / empty at Step 2, omit `rationale` entirely.
- `ide_conversation_id`: only when the user passed `--cid=<value>` inline (direct mode) or picked "I will provide one" and pasted a value at guided-form Step 3. Do NOT invent or guess an id; do NOT reuse `mentor_session_id` here. When present, the writer emits it as the SDK-canonical `mlflow.trace.session` metadata key so downstream `mlflow.search_traces(filter="metadata.mlflow.trace.session=X")` returns this feedback alongside the studio-agent trace for the same conversation. When absent, omit the argument entirely (do not pass an empty string -- the server accepts it but downstream correlation stays orphan for this row).
- `mentor_session_id`: if there is a `mentor_session_id` you have been working with in this conversation, include it so the AI Platform team can co-locate the feedback with the relevant mentor trace. **Must be a UUID** (the server rejects non-UUID strings). Otherwise omit it and the server auto-falls-back to the user's most-recent mentor session on this pod. Server precedence: if both `ide_conversation_id` and `mentor_session_id` are passed, the IDE conversation id wins and `mentor_session_id` is silently dropped from the correlation dict (still recorded for our own debug queries). The server mints a placeholder trace either way, so the feedback still reaches the team.
- `agent_context`: OPTIONAL structured recap of what you were doing when the user invoked `/outsystems-feedback`. Include it when the message clearly refers to a specific tool-call that misbehaved (e.g., "the deploy failed", "the publish returned garbage") -- the recap makes downstream debug much faster. Shape: JSON string ≤2048 bytes with keys like `recent_tool_calls`, `app_key`, `env_key`. Redact secrets / PII (same rule as `rationale`). Skip when the feedback is general ("love the agent", "thumbs-up") -- no tool-call context is relevant.

## Handle the response

- `status: "accepted"` → tell the user "Thanks, feedback sent to the AI Platform team."
- `status: "not_configured"` → the feedback writer is not enabled on this stamp; tell the user "Feedback is not configured on this OutSystems environment yet; I have noted what you said but it did not reach the team."
- Any error (`data.category` of `ValidationError` / `UpstreamError` / `InternalError` / etc., per the SKILL.md error-categories rule) → tell the user "I could not send your feedback right now (<short reason from `data.category`); your message has not been delivered." Do not retry; this is user-initiated and the user can re-invoke `/outsystems-feedback`.

## Scope

Do not volunteer this command. Do not proactively ask "would you like to submit feedback?". Only run this `/outsystems-feedback` flow when the user explicitly types it. `agent_observation` self-reports go through `submit_feedback` directly per the SKILL.md guidance, not through this command.
