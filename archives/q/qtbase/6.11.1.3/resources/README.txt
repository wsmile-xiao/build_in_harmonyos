Runtime data comes from official upstream archives pinned by SHA256 in
conandata.yml:data_sources. The recipe downloads and verifies these in source().
No compressed data archive is included in the source submission.

xkeyboard-config 2.41: install the upstream keyboard data and generate base/evdev
rules using its own map-variants.py and merge.py. Generate the legacy text
inventories from the same upstream XML. xorg aliases are regular file copies.
The earlier diagnostic bundle used Ubuntu 2.41-2ubuntu1.1; its French Ergo-L and
German Noted backports are outside this pinned upstream release.

Adwaita 46.0: install the 34 upstream Xcursor files and copy its 25 aliases from
the upstream Meson mapping as regular files. Keep the upstream index and all
three COPYING notices. Unrelated scalable/symbolic SVGs are excluded at extraction.

IANA 2025b: generate TZif files from checksum-pinned tzcode and tzdata using
the configured native C compiler. All 598 files, including 257 regular-file
aliases, are independent of the build worker's system timezone archive.

The private build runtime is qtbase-runtime. Packaging installs data under
share/X11/xkb, share/icons/Adwaita and share/zoneinfo with provenance and licenses.
An optional QTBASE_DATA_ARCHIVE_DIR can supply the same official archive files
from a local cache; each SHA256 remains mandatory.
