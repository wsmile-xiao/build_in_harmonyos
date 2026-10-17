# whichman

whichman is a small set of fault-tolerant search utilities based on Levenshtein
matching:

- `whichman` searches man page names in `MANPATH`;
- `ftff` searches a directory tree;
- `ftwhich` searches executable files in `PATH`.

## Upstream

- Homepage: https://main.linuxfocus.org/~guido/
- License: GPL-2.0-only
- Language: C

## HarmonyOS adaptation

The 2.4 release is a plain Makefile project with no third-party dependencies.
The Conan recipe supplies the OHOS compiler through `CC`, packages all three
executables and their man pages, and leaves upstream source unchanged.

## Versions

| Version | Status |
|---|---|
| 2.4 | built |
