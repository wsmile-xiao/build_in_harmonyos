# Knowledge evidence: optional I18nQml target and source guard

- Source PR: !7399, head `d11e96035ea3a7f68d4a5d93623f38e65cc96a88`.
- Source archive: knewstuff `6.18.0`, SHA-256 `7e721735abf7e2f6f8c0f42324f885bcad1114c317ac79bfabc705fb8018dba5`.
- Implementation: patch 0001 guards `KF6::I18nQml` link sites with
  `if(TARGET ...)`; patch 0002 defines `HAVE_KLOCALIZEDQMLCONTEXT` in the same
  branch and guards the matching includes, construction, and calls.
- Historical target evidence: CI task `#39871`, raw builder `#45428`, reports a
  successful `conan-build-test` step. The robot summary nevertheless labels
  `test_package` failed. This discrepancy has not been resolved from the raw
  test sub-log and is therefore not counted as a consumer pass.
- Source PR test accounting says upstream `4/4` and consumer `1/1`; this draft
  treats both figures as historical claims pending raw-log confirmation.
- Scope limit: the patch proves the source-level optional-dependency contract;
  it does not prove the dialog's translated QML behavior without I18nQml.
