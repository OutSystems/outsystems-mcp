# CLAUDE.md

Guidance for Claude Code (and other coding agents) when working in this repository.

## Skill docs must stay in lockstep across hosts

This repo ships **three parallel skill documents**:

- `skills/outsystems/SKILL.md` is the Claude Code marketplace skill, consumed when a user runs `claude plugin install outsystems@outsystems`.
- `kiro/outsystems/steering/skill.md` is the Kiro Power steering doc, consumed by Kiro.
- `SKILL.md` at the repo root is the top-level fallback skill doc, consumed by hosts that look at the repo root or by anyone reading the repo on GitHub.

All three carry an identical `## Rules` section, and broadly the same `## Tools at a glance`, `## Caveats`, and `## Workflows` sections. **Any behavioral change to one MUST be applied to all three.** Updating only one creates a host-specific protection gap. For example, a confirm-before-destructive rule added to `skills/outsystems/SKILL.md` alone protects Claude Code users but leaves Kiro Power users (which is how OutSystems uses the skill internally) with no protection.

The common failure mode is to edit only `skills/outsystems/SKILL.md` because the marketplace install path points there. Don't.

### Check before opening a PR

After any skill-doc change, grep for a distinctive phrase from the change across all three files and confirm the count matches:

```bash
PHRASE="<a distinctive substring from your change>"
for f in skills/outsystems/SKILL.md kiro/outsystems/steering/skill.md SKILL.md; do
  printf '%s  %s\n' "$(grep -c "$PHRASE" "$f")" "$f"
done
```

All three counts must be equal. If they aren't, the change is incomplete and the PR will create a host-specific drift.

### Exception: setup / installation flows

Setup steps legitimately diverge between the three (Claude Code uses `claude mcp add`, Kiro Power patches `~/.kiro/settings/mcp.json`, the root SKILL.md describes the wire-level tool names without prescribing a host). The lockstep rule applies to `## Rules` and to behavioral guidance, not to host-specific install recipes.

### Exception: host-specific affordances

Host-specific UI surfaces (typed shortcuts, hotkeys) live only in the doc for the host that has them. The Claude Code marketplace plugin ships slash commands under `commands/` (declared in `.claude-plugin/plugin.json`'s `commands` key); Kiro Powers do not have an equivalent. So mentions of `/feedback` and similar slash-command trigger phrases belong only in `skills/outsystems/SKILL.md`, not in `kiro/outsystems/steering/skill.md` or root `SKILL.md`. The underlying *behavior* (what the agent does on the trigger) still has to lockstep across all three docs.

`commands/` is a Claude-Code-plugin-only directory. There is no Kiro analog and no root analog; do not create one. Behavioral guidance about a command's effect still lands in all three skill docs per the main lockstep rule.

### Manifest version lockstep

Two files declare the plugin version and they must stay in sync on every bump:

- `.claude-plugin/plugin.json` -> `version`
- `.claude-plugin/marketplace.json` -> `plugins[0].version`

`claude plugin update outsystems@outsystems` keys off `marketplace.json`'s version. Forgetting to bump it means users already on the prior version see "already at the latest" and never pull the new content. Always bump both in the same commit.
