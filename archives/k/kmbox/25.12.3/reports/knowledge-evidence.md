# Knowledge evidence: effective read-only permission probe

- Source PR: !7430, head `d045ee587a739762cefc73af681c74325277c4ee`.
- Source archive: kmbox `25.12.3`, SHA-256 `088e88b85686374da855215351e0e5248464921c8b546531d91b8dcef952ff93`.
- Implementation: `patches/0001-Skip-read-only-permission-autotest-on-OHOS.patch`
  checks the owner-write permission bit and an append open after requesting
  read-only mode. It restores the original mode before `QSKIP` in either case.
- Historical target evidence: CI task `#39875`, raw builder `#45432`, completed
  all seven pipeline steps successfully. The platform summary's independent
  `test_package` label conflicted with the raw-step result, so this report
  relies on the builder execution record rather than that label.
- Test accounting recorded by the source PR: upstream CTest `2/2`, installed
  package consumer `1/1`. This extraction introduces no new executed test.
- Scope limit: the skip is conditional on the actual mounted file system;
  it is not an unconditional OS-based waiver and it does not prove behavior on
  mounts where both probes establish effective write denial.
