# squashfs-tools-ng 1.3.2 packaging

Packaging is handled by the Conan recipe (conanfile.py, package_type
"application"). CI builds the package with `conan create` and, after the PR
is merged to main, publishes it to the ohpcd registry via `conan upload`.

- Binaries: gensquashfs, rdsquashfs, sqfs2tar, tar2sqfs, sqfsdiff (bin/)
- Library: libsquashfs static lib + headers (lib/, include/sqfs/)
- Command metadata: ../commands.json (hicmd format, software level)
