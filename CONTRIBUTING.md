# Contributing

Thanks for helping improve Doodle Baseball Expanded.

## Before opening a PR

- Run `python tools/validate_release.py`.
- Run `python -m py_compile launcher.py`.
- Run `node --check payload/dbe-mod.js`.
- Keep the original-game stability rule: custom pitch IDs must not become original engine pitch identities.
- Do not add original third-party game assets/source to this repository.
- For lifecycle-sensitive defense changes, prefer observing/consuming normal game callbacks over deleting/replacing active batter objects.

## Pitch contributions

A pitch should have an identity. Avoid padding the catalog with numbered clones. New signature pitches should have a name that communicates the movement and a behavior that is visually recognizable.

## Pull requests

Describe the player-visible behavior, the code path changed, and how you tested it. Include an F9 debug report when fixing a runtime bug.
