# rpg

Rapid Peptides Generator (`rpg`) performs in-silico digestion of protein
sequences with a configurable enzyme, output format, pKa model, and cleavage
mode.

## Features

- Digest a sequence or FASTA input with the bundled enzyme definitions.
- Report peptide mass and isoelectric-point information.
- Produce FASTA, TSV, and other output formats.
- Support user-defined enzymes through a per-user configuration file.

## OHOS adaptation

Version 1.2.0 is a pure Python application. The Conan package installs the
`rpg` modules under `lib/python` and provides a relocatable `bin/rpg` launcher
that resolves those modules relative to its own package location. No source
patch is required.

The target environment must provide a compatible Python 3 interpreter. The
application creates `rpg_user.py` under the current user's `HOME` directory
when the enzyme module is first loaded.

## Dependencies

- Build and test: Python 3 and pytest 7.4.4.
- Runtime: Python 3.
- Native libraries: none.

## References

- Homepage: https://gitlab.pasteur.fr/nmaillet/rpg
- Release source: https://pypi.org/project/rpg/1.2.0/
