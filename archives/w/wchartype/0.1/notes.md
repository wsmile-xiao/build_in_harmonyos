# wchartype 0.1 adaptation notes

## Package and source

The fixed PyPI ZIP is 1,821 bytes with SHA-256 `1bedb3c5939b9cf75fd35642d9af070a8193d091dacaa5382e3bad00e3f97982`. It contains the pure-Python `wchartype.py`, `setup.py`, and `PKG-INFO`; the package metadata declares MIT and no runtime dependencies, but the archive contains no standalone license text. The Conan recipe installs the module under `lib/python`, adds that path to `PYTHONPATH`, and retains `PKG-INFO` as package documentation.

The only upstream source changes are Python 3 compatibility fixes: use `setuptools.setup` instead of `distutils.core.setup`, and use `chr` instead of `unichr` in two doctest examples. The module's runtime implementation is unchanged.

## Local source checks

On Python 3.11.0rc2, the untouched upstream doctests produced 35/37; the two failures were the `unichr` examples. The patched source passed all 37/37 upstream doctests; `setup.py --name` returned `wchartype`; and the candidate Python files passed `py_compile`. The updated consumer script passed 5/5 local groups, including one file-based mixed-script workflow that reads `test_package/data/mixed-script.txt`, classifies each character through the packaged module, and writes a JSON report. The 13 direct API predicate assertions in the existing category and width checks are unchanged.

## Target validation

On 2026-09-29, the unique H1 runner applied the fixed 11-file candidate ZIP (SHA-256 `173e7bd548bafae68f1fcbf7535d71b472945d925c2af005cccbacd8e5efda14`) to a private HarmonyOS aarch64 framework checkout and ran the affected Conan/W3 consumer once. The actual framework HEAD was `f52bc8aa5dee9e48f06095abc2abafa047607702`; the fixed candidate reference commit was `6f73586b5bb576495579cfb252128037ed5b7f80`. W3 and Conan package creation returned 0. The installed-package consumer passed 5/5 groups, including the mixed-text file workflow, and ran the 37 upstream doctests once, with 37/37 passing. The generated JSON classified all eight input characters and reconstructed the input exactly. The H1 report and full evidence archive are identified as run `wchartype-h1-002`; archive SHA-256 `697c2246b723e310ee9370bb115d85d1145b123e173126e382f91f781fd877c4`; consumer report SHA-256 `dfe5c07365dc32ce8fc5caaee06e2ac33ff250e1fd27b9ecd8a5707fa4ec7428`; mixed-text JSON SHA-256 `37edfbb569d1fa64f7c4147388df7621b862eb2cd8eda7551d5a341af045054c`.

The first H1 preparation attempt stopped before W3 because its path guard rejected the valid `archives/w/wchartype/README.md`; no test process was started. The guard was corrected in the same private root, fixed bytes were rechecked, and W3 ran once. This H1 result validates the candidate files on that framework checkout; it is not an H1 `git rev-parse HEAD` for the local candidate commit or the remote PR.

The existing official CI result #64383 belongs to the earlier remote head `e0920b200a351f2df3a2eff8ba2cc611e7ada440`. It failed in G0 before Conan build/test because the Worker could not spawn `grep` and `wc` (`resource temporarily unavailable`, exit 127). That old-head failure is preserved; it does not replace or contradict the H1 W3 result, and the new candidate has not yet received an official CI result.

No standalone license file exists in the fixed source archive; this is disclosed rather than filled with invented upstream content.

## Contest and workflow status

The official task remains labeled `cpp` while the source is Python. The official AI Worker R47 preflight was run against the fixed checkout and returned `rc=2` (`expected=cpp`, `detected=python`); the result was kept locally and was not submitted. Project review concluded that R47 is specific to the AI Worker path and that the normal manual contribution workflow does not invoke it automatically. Therefore this candidate continues through the manual path with the language difference disclosed; the previous gate result is not a qualification waiver or points guarantee.

At the 2026-09-29 16:02 readback, task #11835 was assigned to `orrkri` and bound to PR #13733, whose published head was still `e0920b200a351f2df3a2eff8ba2cc611e7ada440` (the earlier 10-file candidate). This 11-file candidate has since passed the scoped H1 Conan/W3 consumer run and independent W4 review (P0/P1=0); it has not yet been pushed. PR review was pending with one unresolved test-package opinion, and the old-head official CI failed before Conan/test execution because its Worker could not spawn `grep` and `wc` (exit 127). The Python-source / `cpp` task-label eligibility question remains unresolved; no eligibility or points claim is made. A rebuild was later requested once against the old PR head; its result must not be attributed to this candidate. After publishing this candidate, re-read task binding, review state, and CI specifically for the new head before claiming any of them.
