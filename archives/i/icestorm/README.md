# Project IceStorm

Project IceStorm provides open-source tools for the Lattice iCE40 FPGA
bitstream format.

## HarmonyOS PC adaptation

The recipe builds the native command-line tools without the USB programmer
and validates the installed tools with deterministic command-line checks.

1.1.1 additionally generates and installs the iCE40 device databases
(`share/icebox/chipdb-*.txt`).  Upstream builds these from
`icebox/icebox_chipdb.py`; they are not part of the source tarball, and 1.1
packaged none of them.  1.1.1 also corrects `CHIPDB_SUBDIR` to `icebox`
(upstream `config.mk` default) so `icetime` searches `<prefix>/share/icebox`
rather than `<prefix>/share//share/icebox`.  See `1.1.1/notes.md`.

## Upstream

- Homepage: https://github.com/YosysHQ/icestorm
