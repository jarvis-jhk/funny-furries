# Funny Furries — brief

JARVIS's own reimplementation of **Funny Furries 2 Xmas** (Bastiaan de Jong, 1999, Click & Create),
an arena brawler, red furry vs. blue furry. Jan's goal: play it on Linux / Windows / Steam Deck with
up to four controllers on one shared screen, later online.

Background report (German): /app/agent/data/www/r/t_mv5fgpj6f49n2-*/index.html.
The decompiled original (KlikBack output) and downloads are in /app/agent/data/work/adhoc/ff2/
(`out/` = decompiled project, `dl/` = full version, demo, Part 1 source). Copy what you need into
an untracked `orig/` here — never commit it.

## Rules
- The engine code is ours (C + SDL2, deterministic fixed tick, integer physics, own RNG).
- **Never commit or release the original's graphics, sounds, levels or the .cca file.** The game
  loads them from the player's own copy at first start. Recoloured furries likewise stay out until
  the author agrees. Contacting Bastiaan de Jong goes outside: only with Jan's okay.
- Repo stays private until Jan decides otherwise. Commits use the jarvis-jhk noreply address.
- Jan's domains never appear in the repo, releases or logs. Fault reports go ntfy → GitHub issue,
  like the other games.
- Plan in ROADMAP.md, running state in NOTES.md. Combined game roadmap: `npx tsx /app/agent/scripts/roadmap.ts`.
