# jellyfish

Jellyfish is a tool for fast, memory-efficient counting of k-mers in DNA/RNA.
It provides the `jellyfish` command-line tool and the `libjellyfish-2.0` C++
library.

## Versions

| Version | Status |
| --- | --- |
| 2.3.0 | built |
| 2.3.1 | built |

Homepage: https://github.com/gmarcais/Jellyfish

Usage (after `conan install`): `jellyfish count -m 21 -s 100M -t 4 -C reads.fa -o reads.jf`

Platform note: the generator input mode (`-g`/`-G`) streams sequences through
named pipes, and HarmonyOS rejects `mkfifo(2)`; file-input counting is
unaffected. See `2.3.0/notes.md` and `2.3.1/notes.md`.
