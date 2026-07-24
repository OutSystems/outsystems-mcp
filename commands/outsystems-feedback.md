---
description: Send feedback about your OutSystems agent experience
argument-hint: [--dry-run] [--quiet] [<your feedback>] (leave empty for guided form)
---

The user typed `/outsystems-feedback $ARGUMENTS`. They want to report something about the OutSystems agent experience (a bug, a thumbs-up / thumbs-down, a comment about a tool that misbehaved, etc.).

## Optional flags (direct mode only)

Parse and strip leading flags from `$ARGUMENTS` before deciding the mode:

- `--dry-run` -- Show the exact `submit_feedback` tool call that WOULD be made (name, value, rationale, agent_context, mentor_session_id, mentor_turn_id, ide_conversation_id, experiment_id) as a code block, but do NOT invoke the tool. Reply with the preview and ask the user to confirm ("send it? [y / n]") before firing. On "n" or silence, do not send and say "OK, discarded."
- `--quiet` -- Fire the `submit_feedback` call as normal but skip the confirmation narration on success. On `status: "accepted"`, reply with a single-word acknowledgment ("sent.") instead of the full "Thanks..." block. Errors and `not_configured` still surface with their normal text. Useful for CI-driven or scripted callers.

Both flags may be combined (`--dry-run --quiet` shows the preview without narration decoration). Flags are only recognized in direct mode; the guided-form flow ignores them.

## Two modes

Decide the mode from `$ARGUMENTS` (after stripping leading flags above):

- **Direct mode** -- `$ARGUMENTS` is non-empty and contains at least one non-whitespace character AFTER stripping any leading `--cid=<value>` token. The message body is whatever is left. Skip the guided-form steps and go straight to redaction + tool call.
- **Guided-form mode** -- `$ARGUMENTS` is empty, whitespace-only, OR consists only of a `--cid=<value>` token with no following message. Do NOT reply with an error. Drive the guided form below so the user picks values instead of typing them. This is the closest thing plugins have to Claude Code's built-in `/feedback` modal.

## Guided-form mode

Run these steps IN ORDER. Do not batch them into one `AskUserQuestion` call -- the two picker steps need to happen in sequence so the user's category choice is visible before they type the message.

**Step 1 -- category picker.** Call `AskUserQuestion` exactly once:

- `question`: "What kind of feedback would you like to send?"
- `header`: "Category"
- `multiSelect`: false
- `options` (in this order, each with a concrete example to help disambiguate):
  - `label`: "Thumbs up" -- `description`: "Something worked well or is delightful. Example: 'the mentor turn was fast and the OML edit was exactly what I wanted'."
  - `label`: "Thumbs down" -- `description`: "Something felt off but is not a full bug. Example: 'the deploy took 3 minutes, felt slow' or 'the output was correct but not what I hoped for'."
  - `label`: "Bug report" -- `description`: "Something is broken and should not be. Example: 'publish_start returned OS-BEW-1234 and never recovered'."
  - `label`: "Feature request" -- `description`: "You would like the OutSystems agent to do something it does not currently do. Example: 'I want an env-diff tool that compares two environments'."

Map the user's pick to the `value` argument of `submit_feedback`:

- "Thumbs up" -> `"thumbs-up"`
- "Thumbs down" -> `"thumbs-down"`
- "Bug report" -> `"bug-report"`
- "Feature request" -> `"feature-request"`
- Any custom / "Other" free-text answer the user typed instead of picking -> default `value` to `"bug-report"` and include the user's free-text at the top of the message body.

Do NOT offer numeric ratings ("4", "5") or booleans ("true", "false") in the picker. The server accepts them for schema flexibility, but users find rating scales less intuitive than named tags; a picker of four named categoricals is the whole surface.

**Step 2 -- free-text message.** After the pick lands, reply to the user in a single conversational turn:

> "Got it, <category>. What is the message you would like to include? (Skip this if the category above already says enough -- just reply 'none' or 'skip'.)"

Wait for the user's next message. Treat that message as the raw feedback body (subject to the redaction step below). If the user replies "none" / "skip" / an empty line, use an empty rationale.

**Step 2b -- expected-vs-actual (bug-report only).** If the category picked in Step 1 was "Bug report", ask ONE follow-up question after Step 2:

> "Quick tip: a good bug report has three parts -- what you did, what happened, what you expected. To help the team reproduce: what did you expect to happen instead? (Optional -- reply 'skip' if the message above already covers it.)"

Wait for the user's reply. If they answered anything other than "skip" / empty, combine the two parts into the final `rationale` as:

> Expected: <the Step 2b reply>
>
> Actual: <the Step 2 message>

If they skipped, use the Step 2 message alone. This step fires ONLY for bug reports; thumbs-up / thumbs-down / feature-request keep the single-message rationale from Step 2.

**Step 3 -- optional agent_context clarification (skip when the feedback is clearly general).** After Step 2's message lands, decide whether the message is about a specific tool interaction (e.g., "the deploy failed", "the publish returned garbage", "the diagram tool crashed on merge") vs general sentiment ("love it", "thumbs-up", "not intuitive"). If specific:

- Summarize in ONE sentence what you would attach as `agent_context` (e.g., "I'll include: your last three tool calls were env_info, publish_start (error OS-BEW-1234), and app_traces on app-1").
- Ask "Attach this context to help the team reproduce? [yes / no]".
- If yes, build the JSON blob from your actual tool-call history and use it as `agent_context`. If no, omit `agent_context`.

**Step 3b -- progressive disclosure of correlation ids (only when the message hints at them).** After Step 3, scan the user's message for keywords that suggest they know or care about a specific correlation id:
- "session" / "mentor session" → offer to attach `mentor_session_id` if you have a UUID from a recent mentor tool call in this conversation.
- "trace" / "run" / "runId" / "turn" → offer to attach `mentor_turn_id` from the most recent mentor tool response.
- "conversation" / "conv id" / "cid" → offer to attach `ide_conversation_id` if the user provides one.

Ask a single terse question ("You mentioned 'session' — want me to attach the current mentor session id (a UUID) so the team can jump straight to that turn?"). Skip the entire step when the user's message contains no such keywords. Skip individual offers when the corresponding id is not available in this session's context. Do NOT invent or guess ids; if you don't have one, don't offer to attach it.

If the message is general, skip this step entirely -- do not attach `agent_context`.

Do NOT prompt for a Studio ConversationId. Most users have no way of knowing that opaque id; the server auto-emits `odc.auth_session_id` on every submission (derived from the JWT), which covers per-login grouping without any user action. Advanced users who explicitly want to attach a ConvId can pass `--cid=<value>` inline in direct mode.

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

**Trust note (only when the redaction step actually replaced something).** When the redaction step above found and replaced at least one token / secret / PII, add a one-line reassurance to your redaction acknowledgment: "Your message reaches the OutSystems maintainers with those tokens removed -- it does not go to Anthropic." When nothing was redacted, do NOT add this line -- it would read as a non-sequitur.

## Construct the call

Call the OutSystems `submit_feedback` MCP tool with:

- `name`: `"user_feedback"` -- always for this command. `agent_observation` self-reports go through `submit_feedback` directly per the SKILL.md guidance, not through this command.
- `value`: a one-word categorical tag: `"bug-report"`, `"feature-request"`, `"thumbs-up"`, `"thumbs-down"`. In guided-form mode this comes from Step 1's pick (the mapping is fixed). In direct mode pick the tag that best matches the user's message; default to `"bug-report"` if you cannot tell. **Do NOT** put the user's prose into `value`; the value field is a discrete grouping key. Numeric ratings (`"4"`) and booleans (`"true"`, `"false"`) are accepted by the server for schema flexibility, but do NOT surface them to the user or emit them from this command; users find rating scales less intuitive than named tags. Cap 256 bytes (server rejects longer); single-word tags are well under.
- `rationale`: the full redacted message body (cap 4096 bytes; truncate the tail and tell the user if it was longer). If the guided-form user replied "skip" / "none" / empty at Step 2, omit `rationale` entirely.
- `ide_conversation_id`: only when the user passed `--cid=<value>` inline (direct mode) or picked "I will provide one" and pasted a value at guided-form Step 3. Do NOT invent or guess an id; do NOT reuse `mentor_session_id` here. When present, the writer emits it as the SDK-canonical `mlflow.trace.session` metadata key so downstream `mlflow.search_traces(filter="metadata.mlflow.trace.session=X")` returns this feedback alongside the studio-agent trace for the same conversation. When absent, omit the argument entirely (do not pass an empty string -- the server accepts it but downstream correlation stays orphan for this row).
- `mentor_session_id`: if there is a `mentor_session_id` you have been working with in this conversation, include it so the OutSystems maintainers can co-locate the feedback with the relevant mentor trace. **Must be a UUID** (the server rejects non-UUID strings). Otherwise omit it and the server auto-falls-back to the user's most-recent mentor session on this pod. Server precedence: if both `ide_conversation_id` and `mentor_session_id` are passed, the IDE conversation id wins and `mentor_session_id` is silently dropped from the correlation dict (still recorded for our own debug queries). The server mints a placeholder trace either way, so the feedback still reaches the team.
- `agent_context`: OPTIONAL structured recap of what you were doing when the user invoked `/outsystems-feedback`. Include it when the message clearly refers to a specific tool-call that misbehaved (e.g., "the deploy failed", "the publish returned garbage") -- the recap makes downstream debug much faster. Shape: JSON string ≤2048 bytes with keys like `recent_tool_calls`, `app_key`, `env_key`. Redact secrets / PII (same rule as `rationale`). Skip when the feedback is general ("love the agent", "thumbs-up") -- no tool-call context is relevant.

## Handle the response

- `status: "accepted"` → confirm to the user and, when appropriate, offer a follow-up next step:
  - Bug report / thumbs-down: "Thanks, your feedback has been recorded. If you want, I can also open a Jira ticket with the same context, or add a screenshot if you have one to share."
  - Feature request: "Thanks, your feature request has been recorded. Want me to file it as a Jira story too so it enters the backlog?"
  - Thumbs-up / general: "Thanks, your feedback has been recorded."
  Do NOT name any internal team ("AI Platform team", "Product team", etc.) in the confirmation. Say "recorded" or "sent". The internal routing is not user-visible.
- `status: "not_configured"` → the writer is not enabled on this environment; tell the user "Feedback is not configured on this OutSystems environment yet, so your message was not recorded. If you can share it directly with your OutSystems contact, that will reach the team."
- Any error (`data.category` of `ValidationError` / `UpstreamError` / `InternalError` / etc., per the SKILL.md error-categories rule) → tell the user in plain language what actually blocked the submission, not just the category name. Map the common cases:
  - `ValidationError` with a byte-cap message → "Your message was too long (over 4096 bytes). Trim it and send again."
  - `ValidationError` on `mentor_session_id` shape → "The mentor session id needs to be a UUID. Either drop it (the server will auto-correlate) or paste the exact UUID."
  - `ValidationError` on a reserved name → "'server_failure' is a reserved name only the server uses. Pick 'bug-report' instead."
  - `ValidationError` on a value type → "Feedback value must be a short string, number, or true/false — not an object or null."
  - `UpstreamError` (e.g. 5xx from Databricks) → "The feedback backend is temporarily unreachable. Try again in a minute; if it keeps failing, share the message with your OutSystems contact."
  - `InternalError` or any other category → "Something went wrong on the server (<data.category>). Try again in a minute or share directly with your OutSystems contact."
  Do not retry automatically; this is user-initiated. The point of unpacking the error is to give the user actionable next steps, not to relay implementation details.

## Scope

Do not volunteer this command. Do not proactively ask "would you like to submit feedback?". Only run this `/outsystems-feedback` flow when the user explicitly types it. `agent_observation` self-reports go through `submit_feedback` directly per the SKILL.md guidance, not through this command.
