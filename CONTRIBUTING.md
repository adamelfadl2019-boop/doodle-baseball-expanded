# Contributing

Thanks for helping improve Doodle Baseball Expanded.

Small, focused changes are much easier to review and test than giant rewrites.

## Before opening a pull request

Run:

```bash
python tools/validate_release.py
```

For launcher changes, also test:

```bash
python launcher.py --diagnose --repo "PATH_TO_GAME"
```

For gameplay changes, explain:

- what the player sees,
- what code path changed,
- how you tested it,
- whether it affects pitch identity, hitting, runner lifecycle, or defense.

Include an F9 debug report when it helps.

## Stability rules

- Custom DBE pitch IDs must not replace the original engine's vanilla pitch IDs.
- Avoid lifecycle hacks that delete/replace live batter or runner objects when the original callback can be observed instead.
- Do not add original third-party game assets/source to this repository.
- Keep local-server behavior bound to localhost.
- Do not require administrator privileges.

## Pitch contributions

A pitch should have an identity.

Please avoid:

- numbered clones,
- renamed copies with the same movement,
- huge generated batches added only to increase the count.

A good signature pitch should be recognizable when somebody actually sees it thrown.

## Style / project direction

This project values **quality over feature count**.

If a proposed feature is large, explain why it improves the game enough to justify the complexity.

## Pull requests

Please keep the title simple and describe the change like a person:

Good:

> Fix late foul being counted as strike three

Less useful:

> Comprehensive enhancement of dynamic gameplay state-resolution architecture
