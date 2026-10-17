# unfoo

`unfoo` is an upstream Bash utility for unpacking archives. Version 1.0.8
is obtained from the Gentoo distfiles mirror because the supplied upstream
GitHub repository has only the v1.0.7 tag; the tarball is pinned by SHA256.

The script needs Bash and the selected format's external unpacker at runtime.
The Conan package contains only the upstream `bin/unfoo` script and license;
formats using unace/unrar require those tools to be provided by the consumer.
See `1.0.8/notes.md` for real upstream and OHOS consumer test results.
