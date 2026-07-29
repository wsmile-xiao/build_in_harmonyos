# hwdata-usb 0.409 adaptation notes

This recipe packages only the `usb.ids` subpackage from the immutable upstream
`hwdata` 0.409 release.

The native validation covers every logical check from upstream `make check`.
Two host-tool-dependent checks use documented Path B adaptations when their
required facilities are unavailable. A full pciutils `lspci` still runs the
original dump replay; a reduced implementation without the `-A dump` backend
instead verifies that every record in `lspci-dump.txt` resolves through
`pci.ids`. When privileged Podman is available, the original
`check-usb-ids.sh` runs unchanged; otherwise an offline parser checks USB
vendor/product ordering, scale, and known Linux Foundation root-hub IDs. The
remaining PCI ordering, five UTF-8, and two date checks are unchanged.
The repository also carries three FMF packaging/integration entries; they are
listed separately because they target an installed Fedora/RPM environment.

The added consumer test verifies that Conan propagates `USB_IDS_FILE` through
the consumer run environment and that it references the packaged database. It
then parses the installed USB database, validates ordering, checks Linux
Foundation root-hub IDs, performs a negative lookup, and exercises a
missing-file fault path.
