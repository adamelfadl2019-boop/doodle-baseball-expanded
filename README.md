# Doodle Baseball Expanded

**V19 — GitHub Release Edition**

> An unofficial fan-made expansion layer for the 2019 Doodle Baseball game. It keeps the original game loop and art style, then adds a ridiculous amount of pitching, progression, defense, challenge modes, visual effects, and diagnostics.

`3,000 named pitches` · `16 distinct variants` · `48,000 exact challenges` · `50 signature bosses` · `F9 debug console`

## What makes this version different

V19 is built around one stability rule: **custom pitch IDs never replace the original game's pitch identity.** The original engine still receives its own vanilla pitch IDs; DBE applies named-pitch speed, timing, movement, color, variants, and progression as a separate layer.

### Gameplay

- 3,000 individually named base pitches, including real pitches and handcrafted nonsense such as **Magic Zoomball**, **Invisible Pitch**, **Black Hole**, **Gravity Flip**, **Teleport Curve**, and **Time Freeze**.
- 16 variants that substantially transform the pitch rather than simply renaming it.
- 48,000 exact base-pitch + variant Home Run Gauntlet challenges.
- **Perfectionism**, **Boss Ladder**, **Legendary Rush**, **Mystery Box**, **Arcade Frenzy**, Marathon, Endless, Pitch Lab, and classic-style play.
- Real peanut-fielder pickups, fly outs, force races at first, physical wall rebounds, foul territory, and close SAFE/OUT calls.
- Food-character power and running-speed traits with an in-game trait encyclopedia.
- Mastery medals, achievements, boss cards, mission boards, pitch effects, synthetic SFX, and variant-colored pitcher cues.

### V19 release polish

- A new **HOME** tab gives the mod a proper in-game showcase instead of dropping directly into settings.
- **F9 debug overlay** with FPS, active pitch/variant, current mode, bridge status, fielder count, and event count.
- **DEBUG** tab with self-checks, event history, Safe Mode, copyable GitHub issue reports, and downloadable JSON diagnostics.
- The launcher writes `dbe-build-report.json` with the original `game.js` SHA-256 and every successfully applied patch.
- `launcher.py --diagnose` dry-runs the patcher without changing files.
- GitHub Actions validates Python, JavaScript, pitch counts, unique names, release metadata, and repository layout.

## Installation

This repository intentionally **does not bundle the original game's artwork/assets/source files**. You need a compatible copy of the Doodle Baseball repository separately.

1. Obtain the compatible Doodle Baseball files.
2. Extract this mod anywhere, or place it inside the game repository.
3. On Windows, run `START_REAL_MOD.bat`.
4. Or run `python launcher.py`.
5. The launcher finds the game files, creates separate modded launch files, starts a local server, and opens the mod.

The original `game.js` is not overwritten.

### Useful launcher commands

```bash
python launcher.py --diagnose
python launcher.py --repo "C:/path/to/doodlecricket.github.io-master"
python launcher.py --no-browser
python launcher.py --port 8000
python launcher.py --version
```

## Debugging a bug

Press **F9** in-game. The DEBUG tab can copy a ready-to-paste GitHub issue report or export a JSON report. For installer problems, run:

```bash
python launcher.py --diagnose --repo "C:/path/to/the/game/repo"
```

If the launcher itself fails, it writes `DBE_LAST_ERROR.txt` next to the launcher.

See [DEBUGGING.md](DEBUGGING.md) for the full workflow.

## Preview

Open [`docs/index.html`](docs/index.html) locally, or enable GitHub Pages from the `/docs` folder after publishing the repository.

The full pitch browser is in [`docs/pitches.html`](docs/pitches.html).

## Repository layout

```text
launcher.py                  installer / patcher / local server / diagnostics
payload/dbe-mod.js           main DBE runtime
data/pitches.json            3,000 pitch identities
data/variants.json           variant summary data
docs/                        release preview / pitch browser
.github/                     CI + issue templates
tools/validate_release.py    release validator
```

## Development status

The original roadmap is considered complete in V18/V19. New versions should focus on real playtest bugs, balance, new handcrafted content, and optional campaigns rather than adding systems only to make the feature list longer.

See [ROADMAP.md](ROADMAP.md) and [CHANGELOG.md](CHANGELOG.md).

## Legal / third-party notice

This is an unofficial fan project and is not affiliated with or endorsed by Google. This repository's license applies only to original DBE code/documentation in this repository. It does not grant rights to third-party game assets, trademarks, artwork, or source code. See [THIRD_PARTY_NOTICE.md](THIRD_PARTY_NOTICE.md).
