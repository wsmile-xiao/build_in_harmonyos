# DRAFT-kmbox-25-12-3-readonly-permission-probe

An OHOS file-system mount can accept `QFile::setPermissions(..., ReadOwner)`
without removing owner write access, or still permit an append open. A read-only
test must establish effective write denial before asserting library behavior;
otherwise it should restore state and skip only that unsupported precondition.

## Identity and conclusion

| Field | Value |
|---|---|
| Status | Historical target evidence pending review |
| Proposed route | Supplement the existing OHOS file-system permission knowledge with a Qt test contract |
| Contributor | zxyAtom |
| Source PR | !7430, `d045ee587a739762cefc73af681c74325277c4ee` |
| Delivery PR | Upgrade !7430 in place |
| Package | kmbox/25.12.3 |
| Source | KDE release tarball, SHA-256 `088e88b85686374da855215351e0e5248464921c8b546531d91b8dcef952ff93` |

The repair proves neither that every OHOS mount ignores chmod nor that KMbox is
correct on unsupported mounts. It preserves the original upstream assertion
when the two probes establish the test's read-only precondition.

## Extraction from the ordinary PR

| Original fact | Reusable mechanism | This extraction adds |
|---|---|---|
| The patch checks the owner-write bit after `setPermissions`. | A requested mode is not an observed permission contract. | A two-stage precondition rule. |
| It then attempts append open and restores the saved mode before `QSKIP`. | Permission bits alone are insufficient; effective access must be probed. | The state-restoration requirement and forbidden unconditional skip. |

Original contribution: OHOS test adaptation plus package and consumer tests.
This extraction adds a reusable Qt-file-system test boundary and evidence map.

## Trigger, cause, and repair

`MboxTest::testReadOnlyMbox` assumes that a read-only chmod prevents an owner
append. That assumption is invalid on a mount that retains the write bit or
permits the append. The patch tests both observations. If either disagrees with
the premise, it restores the old mode and uses `QSKIP`; otherwise the original
MBox read-only assertions execute unchanged.

Suggested signature: `File system kept owner write permission|File system allows writes to the chmod read-only mbox test file`.

## Evidence matrix

| ID | Type | Input and command | Result |
|---|---|---|---|
| EVID-01 | static | Patch `0001-Skip-read-only-permission-autotest-on-OHOS.patch`. | Both probes and restoration precede the skip. |
| EVID-02 | historical | CI task `#39875`, builder `#45432`, package source head. | All seven worker steps completed successfully. |
| EVID-03 | historical | Source PR test accounting. | Upstream CTest `2/2`; installed consumer `1/1`. |

The platform summary's independent `test_package` label conflicted with the
raw builder step record. This draft cites the worker record and does not infer
an additional test pass from the summary.

## Test accounting

| Scope | Inventory | Pass | Fail | Skip | Not executed | Basis |
|---|---:|---:|---:|---:|---:|---|
| Upstream CTest | 2 | 2 | 0 | 0 | 0 | Historical source PR record. |
| Installed consumer | 1 | 1 | 0 | 0 | 0 | Historical source PR record. |
| Permission-precondition probes | 2 | 0 | 0 | 0 | 2 | No independent probe-only run was recorded for this extraction. |

## Boundaries and relation to existing knowledge

The current knowledge base has generic HMDFS/chmod permission material. This
is a package-level supplement: it requires both a Qt permission-bit check and
an actual write attempt, and requires restoring the test fixture before skip.
It must not be applied as an unconditional `__OHOS__` exemption.

## Source index and self-check

- Implementation: `archives/k/kmbox/25.12.3/patches/0001-Skip-read-only-permission-autotest-on-OHOS.patch`.
- Evidence report: `archives/k/kmbox/25.12.3/reports/knowledge-evidence.md`.
- CI record: `https://ohpcd.atomgit.com/ci?id=39875`.
- KV and Markdown use the same ID; KV fields are single-line and retain the
  explicit source PR and immutable source commit.
