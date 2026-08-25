# Release checklist

Use this for future public releases or patches.

## Before packaging

- [ ] `python tools/validate_release.py`
- [ ] `python launcher.py --diagnose --repo PATH_TO_GAME`
- [ ] Fresh install from a clean extracted folder
- [ ] Confirm the original `game.js` is not overwritten

## Gameplay smoke test

- [ ] 30+ normal pitches without a broken game state
- [ ] F9 overlay opens and updates
- [ ] Foul at two strikes does not become strike three
- [ ] Real peanut fly catch works
- [ ] Throw to first resolves SAFE/OUT
- [ ] Perfectionism streak builds and resets
- [ ] Boss Ladder advances only after the required result
- [ ] HOME / mode controls still work

## Public files

- [ ] README links work
- [ ] GitHub Pages homepage loads
- [ ] Pitch encyclopedia loads all 3,000 entries
- [ ] CHANGELOG updated
- [ ] release notes updated
- [ ] VERSION matches the release
- [ ] installer ZIP tested after downloading the final artifact

## Publish

- [ ] Create/update tag
- [ ] Upload player installer ZIP
- [ ] Mark stable release as Latest
- [ ] Test the download as a normal player
