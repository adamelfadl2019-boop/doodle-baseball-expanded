# Debugging DBE

## In-game debug console

Press **F9** to toggle the compact runtime overlay. Open **MOD → DEBUG** for the full console.

The console reports:

- FPS
- current mode and pitch system
- active named pitch / variant / challenge ID
- original game bridge readiness
- peanut-fielder bridge count
- character-config bridge count
- defense / foul / wall state
- recent internal events
- launcher build-report metadata when available

### Self-check

**Run self-check** validates the core runtime invariants, including the 3,000-pitch catalog, unique names, 16 variants, game bridge, and optional field/character bridges.

### Safe Mode

**Enable Safe Mode** disables defense, fly outs, force-at-first, foul rules, and wall physics while keeping the core pitch layer active. Use this to determine whether a bug belongs to the stable pitch core or a field-system feature.

### GitHub issue report

**Copy issue report** creates Markdown ready for a GitHub bug issue. **Export debug JSON** downloads a more complete machine-readable report.

The report includes browser/runtime data but does not intentionally include the user's local game folder path.

## Launcher diagnostics

Dry-run all regex patch anchors without modifying the game:

```bash
python launcher.py --diagnose --repo "C:/path/to/game/repo"
```

A successful run prints the original `game.js` SHA-256 and every verified patch.

After a normal install, the launcher writes:

```text
doodle-baseball/mods/dbe-build-report.json
```

If the launcher crashes, inspect:

```text
DBE_LAST_ERROR.txt
```

## Good bug reports

Include:

1. What mode you were playing.
2. The pitch and variant if visible.
3. Exact steps to reproduce it.
4. What you expected.
5. What happened instead.
6. The copied F9 issue report or exported JSON.
7. Whether Debug Safe Mode changes the bug.
