# wiggle

wiggle applies patches to files that are not identical to the ones the
patches were originally generated from — it can extract a diff from two
files, merge a patch with conflict markers, and reverse patches, tolerating
fuzzy context where `patch(1)` would reject the input.

- Upstream: https://github.com/neilbrown/wiggle
- License: GPL-2.0-or-later
- Adapted versions: `1.3/`

## Adaptation summary (1.3)

- Builds the upstream `wiggle` make target directly against `ncurses/6.5`
  (the ohpcd ncurses package ships the static wide-character library, linked
  as `-lncursesw`); every deviation from the upstream Makefile defaults is a
  make command-line override, so the recipe carries zero patches.
- The upstream `dotest` regression suite (71 cases) runs inside the recipe
  `build()`; see `1.3/notes.md` for the counting ledger and evidence.
- The `all` make target is bypassed because it renders the man page via
  `nroff`; the preexisting `wiggle.1` is packaged as documentation.
