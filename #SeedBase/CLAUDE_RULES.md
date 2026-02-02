# Claude Operating Rules (SeedBase)

---

## Core Protocol

1. **Save Seeds to SeedBase** — Every new task gets a Seed in `SEEDS (Intentions)/`. Update Lens 7 (Evolution) as I code. The Seed is my grounding resource.

2. **Reflect Before Creating** — Scan `Fruitful Feedback/` and recent Seeds before planting a new one. History is the map.

3. **Minimize Conversation Re-reading** — Time is expensive. Trust the Seeds and Fruit over scrolling old chat.

4. **Single Entry Point** — `init2.py` is the master application. Everything routes through it. Never treat other files as entry points.

5. **Automatic Pause = Confidence-Based** — Use intuition. High complexity or touching 3+ files? Pause and propose a Seed. Simple fix? Just do it.

---

## Quick Reference

| Trigger | Action |
|---------|--------|
| New feature request | Pause → Read Fruit → Propose Seed |
| Bug fix (1-2 files) | Execute directly, log in active Seed |
| Schema/API change | Always Seed first |
| UI component | Seed if new, inline if styling existing |

---

## Session Start Checklist

1. Read `CLAUDE_RULES.md` (this file)
2. Read latest `Fruitful Feedback/*.md`
3. Identify active Seeds
4. Ask: "Which Seed are we cultivating?"

---

*Last Updated: 2026-02-01*
