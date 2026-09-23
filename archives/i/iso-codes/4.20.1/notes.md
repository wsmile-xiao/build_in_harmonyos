# iso-codes 4.20.1 adaptation notes

The 4.20.1 release moved from Autotools to Meson. It has no target runtime
dependency: Meson, Ninja, Python, and gettext are build-host tools.

The upstream UTF-8 test used a working-directory-relative glob which could
inspect zero `.po` files. The first patch resolves each domain relative to the
test script and fails closed on an empty inventory. The second patch repairs
three generated XML defects: unescaped attribute characters, the absent ISO
3166-3 branch, and the missing final ISO 3166-2 country group.

Local OHOS/armv8 `conan create` r6 passed all 8 upstream tests and a consumer
validator with 1513 assertions. The consumer parses 16 JSON/schema files and
all 8 XML files, compares XML record counts with JSON, checks 5 compatibility
links, validates pkg-config metadata, and checks all 708 canonical `.mo`
catalogs.

Target W3 run `iso-codes-4.20.1-w3-r1` used one launch on
`10.62.150.125:8022`. The frozen validator confirmed the same package state
and 1513 assertions, then verified the runner and task-owned remote root were
absent after release.
