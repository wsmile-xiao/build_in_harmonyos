# ki18n 6.18.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline. It updates the
published 6.14.0 HarmonyOS PC recipe to KDE Frameworks 6.18.0 while keeping
the core `KF6::I18n` library usable by downstream packages.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_WITH_QML=ON` since the 6.18.0.1 revision: qtdeclarative/6.11.1 is
  published, so the QML add-on `libKF6I18nQml.so` (`KLocalizedQmlContext`) is
  shipped for KF6NewStuff (contrib-3596). The 6.18.0 note "Qt6 Qml not
  published" is stale.
- The QML runtime needs qtdeclarative's `<pkg>/qml` tree on
  `QML2_IMPORT_PATH`/`QML_IMPORT_PATH`; without it `ki18ndeclarativetest`
  fails with `module "QtQml" is not installed`.
- `KF_SKIP_PO_PROCESSING=ON` avoids building translation catalogs in the
  cross-build package path.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during Conan build.
- The OHOS runner excludes `kcatalogtest`, `kcountrytest`,
  `kcountrysubdivisiontest`, and `ktimezonetest` because the optional
  upstream iso-codes runtime data is not currently available.
- `gettext/0.22.5.1` remains required for `LibIntl`, which the library links
  against on non-glibc platforms.
- `KF6I18nMacros.cmake.in` is patched so consumers are not forced to find the
  Gettext command-line tools when only linking `KF6::I18n`.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `d0cbfbf3427c0368daa23f9f68b3cb5b03ad37b6820591491b3ea8a0a28bea61`.
- The consumer macro patch was checked against the unpacked 6.18.0 source.

OHOS `conan create` verification passed on 2026-09-30 (revision 6.18.0.1).

- Local log: `reports/conan-create-run2.log` (plus the W3 run in
  `reports/w3-local-ci.log`).
- Upstream CTest: **12/12 executed tests passed** (registered 16, excluded 4);
  the extra test versus 6.18.0 is `ki18ndeclarativetest`, enabled by
  `BUILD_WITH_QML=ON`.
- Excluded upstream CTest entries: `kcatalogtest`, `kcountrytest`,
  `kcountrysubdivisiontest`, `ktimezonetest` — each measured, they fail with
  `Unable to open iso_3166-1.json` (no `iso-codes` package in ohpcd).
- Conan `test_package`: PASS (`test_ki18n`, 6 checks: 5 `CHECK` assertions +
  the final all-pass verdict).
- Runner results: L0 pass, L1 pass, L4 pass; L2 skip: no bin/ dir; L5 fail
  (pre-existing SONAME telemetry, non-blocking — see below).

## L5 产物基线（如实记录，W4 审计 P2 整改）
- 本包 W3 的 L5 真实结果：**fail: soname_gate_failed**（L5a 无 DT_SONAME ×3、L5b `../../bin` NEEDED ×2、L5c IMPORTED_NO_SONAME ×1）。conan-verify-report.md 中"L5: ✅ PASS"为 conan-verify 独立探测口径（工具差异），以 w3-local-ci.log 为准。
- 定性：**非阻断存量遥测门禁**——build_and_test.sh L5 段注释自证"基于 SONAME 存量扫描报告，覆盖 23 个已知缺陷"；脚本中 L5_RESULT 不参与 FAILED++/exit 1（仅 L0/L1/KC/JC 阻断）；实证：ktextwidgets #7104 同类 L5 fails ×3 而远端 CI 绿。
- 同构性：已发布的 ki18n/6.18.0（readelf 实测无 SONAME + LocaleData `../../bin` NEEDED）与本包完全一致；sonnet/6.26.0 的 SonnetUi 同样 NEEDED `../../bin/libKF6SonnetCore.so`。根因是 KF6/OHOS 构建全线未启用库版本化（SOVERSION），属平台级存量议题，单包配方不越权改动 ECM 全局行为。
- 消费者可用性：kxmlgui/ktextwidgets 同款农场方案（`<build>/../bin` 软链 + cwd）已在两笔已合并 PR 上验证有效。
---

**编译结束**: 2026-09-30 12:21
**最终状态**: built
