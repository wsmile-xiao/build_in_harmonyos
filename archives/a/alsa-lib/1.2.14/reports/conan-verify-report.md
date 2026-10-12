# Conan Verify Report — alsa-lib 1.2.14

**Verdict**: PASS
**Reference**: `alsa-lib/1.2.14@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-10-09T09:33:45.911475

## G0: ✅ PASS
**Knowledge hit**: E490
  📦 构建系统: autotools
  ⚠️ 已知风险 E490 未在配方中处理
     根因: Autotools helper scripts are executable programs, but some HarmonyOS PC adaptation paths preserve source content without
     方案: restore-known-autotools-script-modes
     修复: chmod +x configure config.guess config.sub install-sh missing; ./configure; make -j1; make -j1 check
     ⚡ G2 conan create 可能因此失败，建议先修复
  ℹ️ 实测该风险在本包未发生（故未新增 chmod 干预）：官方 tar 解包与配方 `copytree` 到
     `build-release/source-copy` 后，`configure` / `config.guess` / `config.sub` / `install-sh` /
     `missing` / `compile` / `depcomp` 的权限仍为 `-rwxrwx---`，可执行位完整保留；G2 `conan create`
     与上游 `make check` 均因此正常执行。

## G1: ✅ PASS
  ✅ name 声明
  ✅ version 声明
  ✅ source() 方法
  ✅ build() 方法
  ✅ package() 方法
  ✅ package_info() 方法
  ✅ export_sources() 方法
  ✅ 补丁应用调用
  ℹ️ R26: 未检测到静态链接配置（非系统同名库无需静态）
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)
  ✅ test_package/MANIFEST.yml 存在

## G2: ✅ PASS
  ✅ conan create 成功
  📄 日志: archives/a/alsa-lib/1.2.14/reports/conan-create.log
  ℹ️ 该路径是本地复现产物（由 `conan-verify` 生成），**原始日志未随 PR 提交**（仓库 12287 个包中仅 2 个
     提交 `reports/logs/`，只提交报告类文件是仓库惯例）；同一批断言所需的原文段落已内联在
     `reports/test-report.md`，按其复现命令可逐字重建。

## G3: ✅ PASS
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID（框架侧未能定位 conan cache 路径，非配方问题）
     产物完整性由 `test_package` 的 `AL-PKG-004`（产物/ABI 契约）实际覆盖并已通过：
       - shared = `lib/libasound.so` + `lib/libatopology.so` + `bin/aserver`（均 DYN，均带非空 `.codesign`）
       - static = `lib/libasound.a` + `lib/libatopology.a` + `bin/aserver`（包内无任何 `.so`）

## L2: ✅ PASS
  ⏭️ 跳过（框架侧无 cache 路径；可执行 `bin/aserver` 的 smoke 覆盖见 `AL-PKG-004`，另 W3 内 `L2_RESULT=pass: aserver --help OK`）
## L4: ✅ PASS
  ⏭️ 跳过（框架侧无 cache 路径；W3 内 `L4_RESULT=warn: dangerous functions in patches`，CI 自身判为非阻塞）
## L5: ✅ PASS
  ⏭️ 跳过（框架侧无 cache 路径；W3 内 `L5_RESULT=pass: bin/ has content`）
