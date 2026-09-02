---
description: Send feedback about your OutSystems agent experience
argument-hint: [--dry-run] [--quiet] [<your feedback>] (leave empty for guided form)
---

The user typed `/outsystems-feedback $ARGUMENTS`. They want to report something about the OutSystems agent experience (a bug, a thumbs-up / thumbs-down, a comment about a tool that misbehaved, etc.).

## Optional flags (direct mode only)

Parse and strip leading flags from `$ARGUMENTS` before deciding the mode:

- `--dry-run` -- Show the exact feedback tool call that WOULD be made (name, value, rationale, agent_context, mentor_session_id, mentor_turn_id, experiment_id) as a code block, but do NOT invoke the tool. Reply with the preview and ask the user to confirm ("send it? [y / n]") before firing. On "n" or silence, do not send and say "OK, discarded."
- `--quiet` -- Fire the feedback call as normal but skip the confirmation narration on success. On `status: "accepted"`, reply with a single-word acknowledgment ("sent.") instead of the full "Thanks..." block. Errors and `not_configured` still surface with their normal text. Useful for CI-driven or scripted callers.

Both flags may be combined (`--dry-run --quiet` shows the preview without narration decoration). Flags are only recognized in direct mode; the guided-form flow ignores them.

## Two modes

Decide the mode from `$ARGUMENTS` (after stripping leading flags above):

- **Direct mode** -- `$ARGUMENTS` is non-empty and contains at least one non-whitespace character. The message body is whatever is left. Skip the guided-form steps and go straight to redaction + tool call.
- **Guided-form mode** -- `$ARGUMENTS` is empty or whitespace-only. Do NOT reply with an error. Drive the guided form below so the user picks values instead of typing them. This is the closest thing plugins have to Claude Code's built-in `/feedback` modal.

## Guided-form mode

Run these steps IN ORDER. Do not batch them into one `AskUserQuestion` call -- the two picker steps need to happen in sequence so the user's category choice is visible before they type the message.

**Step 1 -- category picker.** Call `AskUserQuestion` exactly once:

- `question`: "What kind of feedback would you like to send?"
- `header`: "Category"
- `multiSelect`: false
- `options` (in this order, each with a concrete example to help disambiguate):
  - `label`: "Thumbs up" -- `description`: "Something worked well or is delightful. Example: 'the mentor turn was fast and the OML edit was exactly what I wanted'."
  - `label`: "Thumbs down" -- `description`: "Something felt off but is not a full bug. Example: 'the deploy took 3 minutes, felt slow' or 'the output was correct but not what I hoped for'."
  - `label`: "Bug report" -- `description`: "Something is broken and should not be. Example: 'the publish call returned OS-BEW-1234 and never recovered'."
  - `label`: "Feature request" -- `description`: "You would like the OutSystems agent to do something it does not currently do. Example: 'I want an env-diff tool that compares two environments'."

Map the user's pick to the `value` argument of the feedback call:

- "Thumbs up" -> `"thumbs-up"`
- "Thumbs down" -> `"thumbs-down"`
- "Bug report" -> `"bug-report"`
- "Feature request" -> `"feature-request"`
- Any custom / "Other" free-text answer the user typed instead of picking -> default `value` to `"bug-report"` and include the user's free-text at the top of the message body.

Do NOT offer numeric ratings ("4", "5") or booleans ("true", "false") in the picker. The server accepts them for schema flexibility, but users find rating scales less intuitive than named tags; a picker of four named categoricals is the whole surface.

**Step 2 -- free-text message.** After the pick lands, reply to the user in a single conversational turn:

> "Got it, <category>. What is the message you would like to include? (Skip this if the category above already says enough -- just reply 'none' or 'skip'.)"

Wait for the user's next message. Treat that message as the raw feedback body (subject to the redaction step below). If the user replies "none" / "skip" / an empty line, use an empty rationale.

**Step 2b -- expected-vs-actual (bug-report only).** If the category is "Bug report" (picked at Step 1, or pre-filled by the skill doc's bounded-exception entry point that skips Step 1), ask ONE follow-up question after Step 2:

> "Quick tip: a good bug report has three parts -- what you did, what happened, what you expected. To help the team reproduce: what did you expect to happen instead? (Optional -- reply 'skip' if the message above already covers it.)"

Wait for the user's reply. If they answered anything other than "skip" / empty, combine the two parts into the final `rationale` as:

> Expected: <the Step 2b reply>
>
> Actual: <the Step 2 message>

If they skipped, use the Step 2 message alone. This step fires ONLY for bug reports; thumbs-up / thumbs-down / feature-request keep the single-message rationale from Step 2.

**Step 3 -- optional agent_context clarification (skip when the feedback is clearly general).** After Step 2's message lands, decide whether the message is about a specific tool interaction (e.g., "the deploy failed", "the publish returned garbage", "the diagram tool crashed on merge") vs general sentiment ("love it", "thumbs-up", "not intuitive"). If specific:

- Entering from the skill doc's bounded exception: skip the yes/no ask below -- the prompt already asked and the user already agreed. Build the JSON blob directly from the failing tool call: `error_details.step` is the tool name, `error_details.message` is the verbatim error text (including its error code and any pod/build identifier it carried), redacted per the redaction step, so the prompt's promise is honored.
- Otherwise: summarize in ONE sentence what you would attach as `agent_context` (e.g., "I'll include: your last three tool calls were an environment lookup, the publish call (error OS-BEW-1234), and an app-traces lookup on app-1"), ask "Attach this context to help the team reproduce? [yes / no]", and build the JSON blob from your actual tool-call history only if yes. If no, omit `agent_context`.

**Step 3b -- progressive disclosure of correlation ids (only when the message hints at them).** After Step 3, scan the user's message for keywords that suggest they know or care about a specific correlation id:
- "session" / "mentor session" → offer to attach `mentor_session_id` if you have a UUID from a recent mentor tool call in this conversation.
- "trace" / "run" / "runId" / "turn" → offer to attach `mentor_turn_id` from the most recent mentor tool response.

Ask a single terse question ("You mentioned 'session' — want me to attach the current mentor session id (a UUID) so the team can jump straight to that turn?"). Skip the entire step when the user's message contains no such keywords. Skip individual offers when the corresponding id is not available in this session's context. Do NOT invent or guess ids; if you don't have one, don't offer to attach it.

If the message is general, skip this step entirely -- do not attach `agent_context`.

Then proceed to the redaction step below with the values collected across steps 1-3.

## Redaction step (mandatory, unconditional)

Applies to both modes. Before constructing the tool call, scan the message body (from direct-mode args or guided-form Step 2) and replace each of these with `[redacted]`:
- Bearer tokens, JWTs, API keys, passwords, OAuth client secrets
- PII (email addresses, full names, phone numbers from any User entity)
- Code snippets and OML
- Full transcripts of multi-turn dialogue

After redacting, tell the user what you replaced. The redacted text is what you use below.

**Trust note (only when the redaction step actually replaced something).** When the redaction step above found and replaced at least one token / secret / PII, add a one-line reassurance to your redaction acknowledgment: "Your message reaches the OutSystems maintainers with those tokens removed -- it does not go to Anthropic." When nothing was redacted, do NOT add this line -- it would read as a non-sequitur.

## Correlation-id offer (mandatory when the message hints)

Applies to BOTH modes. Before or alongside constructing the tool call, scan the redacted message body for these keywords:

- `session`, `mentor session` -> the user hinted they may know the `mentor_session_id`.
- `turn`, `mentor turn`, `trace`, `runId`, `run` -> the user hinted they may know the `mentor_turn_id`.

If any of these appear, the agent MUST include an offer in its reply. The offer is phrased so the user can act on it (share an id, or say no) and is mandatory even if the submission has already fired -- silently omitting the correlation without acknowledging the hint is not acceptable.

Preferred flow (interactive session): ask BEFORE submitting.

> "You mentioned a mentor [session|turn] -- do you have the id you want this tied to? If not, I'll submit without it and the server will auto-correlate to your most-recent one where it can."

Then wait for the user's reply. If they respond with an id, attach it verbatim in the corresponding field (`mentor_session_id` must be a UUID; `mentor_turn_id` is opaque ≤256 bytes). If they say no or reply without an id, submit without and do NOT re-ask this session.

Acceptable alternative when interactive back-and-forth is not possible (fast-path direct mode, scripted callers, one-shot invocations): submit with the id null AND include the offer as an actionable follow-up in the confirmation:

> "Sent. If you have the [session|turn] id you want this tied to, share it and I'll resubmit with correlation attached."

What is NOT acceptable: submitting without the id AND without an offer, then only explaining post-hoc that no id was available. The user's mention of `session` or `turn` is the hint; the agent must honor it.

Scope rules:

- Only ask about the id-level the user hinted at. `session` in the message does not unlock the `mentor_turn_id` ask, and vice versa.
- Skip the entire step when the message contains NO such keywords -- silent submission is correct.
- Skip the offer when you already have the id in scope from your current conversation (a mentor tool call earlier in this session gave you a UUID) -- attach it directly without asking, and confirm in the reply which id you attached.
- Do NOT invent or guess ids. If the user says "yes I have it" but the value they paste is not shaped like an id (e.g. not a UUID for `mentor_session_id`), tell them and skip the field rather than pass junk.

## Construct the call

Call the OutSystems feedback tool with:

- `name`: `"user_feedback"` -- always for this command. `agent_observation` self-reports go through the feedback tool directly per the SKILL.md guidance, not through this command.
- `value`: a one-word categorical tag: `"bug-report"`, `"feature-request"`, `"thumbs-up"`, `"thumbs-down"`. In guided-form mode this comes from Step 1's pick (the mapping is fixed), or from the skill doc's pre-fill when entering at Step 2 per the Scope section's bounded exception. In direct mode pick the tag that best matches the user's message; default to `"bug-report"` if you cannot tell. **Do NOT** put the user's prose into `value`; the value field is a discrete grouping key. Numeric ratings (`"4"`) and booleans (`"true"`, `"false"`) are accepted by the server for schema flexibility, but do NOT surface them to the user or emit them from this command; users find rating scales less intuitive than named tags. Cap 256 bytes (server rejects longer); single-word tags are well under.
- `rationale`: the full redacted message body (cap 4096 bytes; truncate the tail and tell the user if it was longer). If the guided-form user replied "skip" / "none" / empty at Step 2, omit `rationale` entirely.
- `mentor_session_id`: if there is a `mentor_session_id` you have been working with in this conversation, include it so the OutSystems maintainers can co-locate the feedback with the relevant mentor trace. **Must be a UUID** (the server rejects non-UUID strings). Otherwise omit it and the server auto-falls-back to the user's most-recent mentor session on this pod.
- `agent_context`: OPTIONAL structured recap of what you were doing when the user invoked `/outsystems-feedback`, or of the failing tool call when entering from the skill doc's bounded exception (Step 3 above). Include it when the message clearly refers to a specific tool-call that misbehaved (e.g., "the deploy failed", "the publish returned garbage") -- the recap makes downstream debug much faster. Shape: JSON string ≤2048 bytes with keys like `recent_tool_calls`, `app_key`, `env_key`, and an `error_details` sub-key (`step`: the tool name, `message`: the verbatim error text including its error code and any pod/build identifier) per `skills/outsystems/SKILL.md`'s `agent_context` convention. Redact secrets / PII (same rule as `rationale`). Skip when the feedback is general ("love the agent", "thumbs-up") -- no tool-call context is relevant.

## Handle the response

- `status: "accepted"` → confirm to the user and, when appropriate, offer a follow-up next step. Keep the confirmation short and never name internal tools, ticketing systems, or team names (no "Jira", "Confluence", "AI Platform team", "Product team", etc.). Say "recorded" or "sent". The internal routing is not user-visible.
  - Bug report / thumbs-down: "Thanks, your feedback has been recorded. If a screenshot or steps to reproduce would help, share them and I'll attach them."
  - Feature request: "Thanks, your feature request has been recorded. Anything else you'd like to add — a use case, an example, a mock?"
  - Thumbs-up / general: "Thanks, your feedback has been recorded."
- `status: "not_configured"` → the writer is not enabled on this environment; tell the user "Feedback is not configured on this OutSystems environment yet, so your message was not recorded. If you can share it directly with your OutSystems contact, that will reach the team."
- Any error (`data.category` of `ValidationError` / `UpstreamError` / `InternalError` / etc., per the SKILL.md error-categories rule) → tell the user in plain language what actually blocked the submission, not just the category name. Map the common cases:
  - `ValidationError` with a byte-cap message → "Your message was too long (over 4096 bytes). Trim it and send again."
  - `ValidationError` on `mentor_session_id` shape → "The mentor session id needs to be a UUID. Either drop it (the server will auto-correlate) or paste the exact UUID."
  - `ValidationError` on a reserved name → "'server_failure' is a reserved name only the server uses. Pick 'bug-report' instead."
  - `ValidationError` on a value type → "Feedback value must be a short string, number, or true/false — not an object or null."
  - `UpstreamError` (5xx from the downstream store — do NOT name the store to the user) → "The feedback backend is temporarily unreachable. Try again in a minute; if it keeps failing, share the message with your OutSystems contact."
  - `InternalError` or any other category → "Something went wrong on the server (<data.category>). Try again in a minute or share directly with your OutSystems contact."
  Do not retry automatically; this is user-initiated. The point of unpacking the error is to give the user actionable next steps, not to relay implementation details.

## Scope

Do not volunteer this command. Do not proactively ask "would you like to submit feedback?". Only run this `/outsystems-feedback` flow when the user explicitly types it. Two exceptions, both defined in the skill doc: the once-per-session bounded prompt after a clearly-broken failure (enter at Step 2 with `value` pre-filled to `bug-report`), and a user who asks how to give feedback. `agent_observation` self-reports go through the feedback tool directly per the SKILL.md guidance, not through this command.
