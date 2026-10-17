# DRAFT-knewstuff-6-18-0-optional-i18nqml

Making `KF6::I18nQml` optional requires more than conditional linking. The
sources also include and construct `KLocalizedQmlContext`; guard those source
uses with the same feature condition, otherwise a target-guarded build still
contains unresolved declarations or unavailable headers.

## Identity and conclusion

| Field | Value |
|---|---|
| Status | Pending raw consumer-result confirmation |
| Proposed route | New package-specific optional-target knowledge candidate |
| Contributor | zxyAtom |
| Source PR | !7399, `d11e96035ea3a7f68d4a5d93623f38e65cc96a88` |
| Delivery PR | Upgrade !7399 in place |
| Package | knewstuff/6.18.0 |
| Source | KDE Frameworks tarball, SHA-256 `7e721735abf7e2f6f8c0f42324f885bcad1114c317ac79bfabc705fb8018dba5` |

The current evidence verifies the dependency-to-source guard design and a
successful `conan-build-test` worker step. The CI comment's `test_package`
classification conflicts with that successful step; this draft does not claim
that the installed consumer passed until its raw sub-log is reconciled.

## Extraction from the ordinary PR

| Original fact | Reusable mechanism | This extraction adds |
|---|---|---|
| Patch 0001 wraps every `KF6::I18nQml` link in `if(TARGET ...)`. | Optional CMake targets need an explicit capability check. | A target-to-source coupling requirement. |
| Patch 0002 defines `HAVE_KLOCALIZEDQMLCONTEXT` only inside the same branch. | C++ references must share the CMake feature boundary. | Guards for include, construction, and context-object use. |

Original contribution: KNewStuff packaging, test package, and two source
patches. This extraction adds the causal rule that link guards alone are not a
complete optional-dependency repair.

## Trigger, cause, and repair

The trigger is a build that lacks `KF6::I18nQml` but still compiles the dialog
or widgets sources. The original code unconditionally included and used
`KLocalizedQmlContext`. The repair couples `if(TARGET KF6::I18nQml)` to a
compile definition, and uses that definition for all dependent source sites.

Suggested signature: `KF6::I18nQml|KLocalizedQmlContext|HAVE_KLOCALIZEDQMLCONTEXT`.

## Evidence matrix

| ID | Type | Input and command | Result |
|---|---|---|---|
| EVID-01 | static | Patch 0001 at source head. | Link sites are conditional on target existence. |
| EVID-02 | static | Patch 0002 at source head. | All edited `KLocalizedQmlContext` uses share the compile guard. |
| EVID-03 | historical | CI task `#39871`, builder `#45428`. | `conan-build-test` is marked successful; consumer sub-result remains unresolved. |

## Test accounting

| Scope | Inventory | Pass | Fail | Skip | Not executed | Basis |
|---|---:|---:|---:|---:|---:|---|
| Upstream tests | 4 | 0 | 0 | 0 | 4 | PR body reports `4/4`; raw evidence has not yet been reconciled. |
| Installed consumer | 1 | 0 | 0 | 0 | 1 | Robot summary says failed while the worker step is successful. |
| Static source guards | 2 | 2 | 0 | 0 | 0 | One target guard and one source guard family inspected. |

The historical PR ratios are retained in the evidence report as claims, not
converted into this draft's pass count until the raw test log is available.

## Boundaries and relation to existing knowledge

Search scope covered current drafts, formal documents, and graph entries for
`I18nQml`, `KLocalizedQmlContext`, and optional CMake targets. No matching
package-specific draft was found. This pattern is only valid when the affected
code has a sound non-I18nQml behavior; it does not prove translated QML context
availability in the feature-off configuration.

## Source index and self-check

- Patches: `archives/k/knewstuff/6.18.0/patches/0001-Guard-optional-KF6-I18nQml-target.patch` and `0002-Guard-KLocalizedQmlContext-usage.patch`.
- Evidence report: `archives/k/knewstuff/6.18.0/reports/knowledge-evidence.md`.
- CI record: `https://ohpcd.atomgit.com/ci?id=39871`.
- The KV and Markdown share an ID and `doc_file`; unknown consumer execution
  is recorded as unexecuted instead of passed.
