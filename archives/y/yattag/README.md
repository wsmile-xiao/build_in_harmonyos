# yattag

`yattag` is a pure Python library for generating HTML and XML documents.

This archive contains the OpenHarmony PC Conan recipe for version 1.16.1.
The package installs its Python modules under `lib/python/yattag` and exposes
them through Conan's `PYTHONPATH` run environment.

The upstream project is distributed under LGPL-2.1. The platform task currently
labels this software as C++, while its upstream source is Python; this archive
records the source facts and does not change the platform classification.

On OpenHarmony aarch64, H1 #005 verified the Conan recipe and two separate
package consumers. The new OHOS consumer imported the actual package, generated
HTML, saved and read it as UTF-8 in the private Conan build folder, and parsed
the saved content. Local W3 passed; the complete framework `finish` returned 1
with reported failed steps `step5b` and `step8` in legacy closeout checks.
The independent G0 `configure` check separately returned 127 for this pure
Python sdist. The unchanged upstream suite passed 28/28 in H1 #001 for the same sdist.
Published PR #13609 passed official CI #63990 on its previous head
`ac332226cbed49aba097570eb03cdd32cf8427a1`, then received review FAIL
for its body field and missing OHOS consumer category. That old CI does not
validate the review fix; current-head CI and AI must be checked after updating
the PR. The H1 #005 raw evidence is retained outside this PR.
