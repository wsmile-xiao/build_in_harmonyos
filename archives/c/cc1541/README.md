# cc1541

cc1541 creates Commodore 1541 floppy disk images in D64 (35 and 40 track),
G64, D71 or D81 format, with control over data layout, custom sector
interleaving and extended-track BAM formatting (SPEED DOS / DOLPHIN DOS).
The `4.2` recipe builds the upstream plain-Makefile target with clang and
packages the `cc1541` executable; it declares no Conan package dependencies.

The upstream Bitbucket workspace (PTV_Claus/cc1541) is currently deactivated
by Bitbucket, so the packaged 4.2 source zip is the author-published release
artifact on CSDb (release id 240041), which the official documentation site
links to for downloads.
