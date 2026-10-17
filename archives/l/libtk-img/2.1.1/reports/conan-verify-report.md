# Conan Verify Report — libtk-img 2.1.1

**Verdict**: PASS
**Reference**: `libtk-img/2.1.1@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-10-09T10:41:56.720987

## G0: ✅ PASS
**Knowledge hit**: E490
  📦 构建系统: autotools
  ⚠️ 已知风险 E490 未在配方中处理
     根因: Autotools helper scripts are executable programs, but some HarmonyOS PC adaptation paths preserve source content without
     方案: restore-known-autotools-script-modes
     修复: chmod +x configure config.guess config.sub install-sh missing; ./configure; make -j1; make -j1 check
     ⚡ G2 conan create 可能因此失败，建议先修复

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
  📄 日志: archives/l/libtk-img/2.1.1/reports/conan-create.log

## G3: ✅ PASS
  ℹ️ 无 bin/ 目录（可能是纯库包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

---

## 备注（人工补充）

- **日志留存**：上文 G2 引用的 `reports/conan-create.log` 是**本地产物，未随 PR 提交**
  （`reports/` 被 `.gitignore` 忽略；PR 只带 `test-report.md` / `conan-verify-report.md` / `pr-body.md`）。
  本地复现见 `reports/test-report.md` §4.1 / §5。
- **G0 知识条目 E490（autotools helper 可执行位）未发生**：该条目给出 ⚡ 预警，
  但本次 **G2 `conan create` 实测通过**（tar 解包 + `copytree` 后 `configure`/`config.guess`/
  `config.sub`/`install-sh`/`missing` 仍保留可执行位），无需额外 `chmod`。
- **G0 干净构建验证（`ohc clean-verify`）为「预期行为」，非失败**：该步骤只跑裸 `./configure`、
  **不执行 `build()`**，故无法复现本 recipe 在 `build()` 内的运行时修复
  （E011 `umask 077→022`、`config.guess` 桩、Makefile 路径修补）→ `configure` 报
  `<tcl包>/lib directory doesn't contain tclConfig.sh`。`clean_verify.py` 据此判为「预期行为」、
  不阻塞（真实构建证据由 G2 + W3 提供）。
- **W3 本地 CI 模拟（`ci/conan/setup.sh` + `build_and_test.sh`）全通过**：
  `L0_RESULT=pass`、`L1_RESULT=pass`（含 `L1e` 破坏性反向测试：搬走 `lib/`+`include/` 后消费者测试
  确实失败 → 证明测试真实依赖本包）、`L2_RESULT=skip`（无 bin/）、`L4_RESULT=pass`、`L5_RESULT=pass`，
  `Junk Files: 0`（prdiff 模式），`Success: 1 / Pass rate: 100.0%`。
  日志：`reports/w3-local-ci.log`（本地产物，未随 PR 提交）。
- **`ohc finish` 端到端 `FINISH_RC=0`**（`✅ 编译收尾全部完成`）：`一致性问题 0`、`submit 就绪` 四项全 ✅；
  唯一告警为「缺少 release tar.gz」（纯 dlopen 扩展无独立程序，见 `packaging/README.md`，该告警全仓普遍）。
- **Reference 说明**：本报告 `Reference` 值 `libtk-img/2.1.1@ohpcd/stable` 是工具本地验证形态
  （`conan_verify.py` 默认 `--user=ohpcd --channel=stable`）；**CI/发布的制品引用是不带 user/channel 的
  `libtk-img/2.1.1`**（`ci/conan/upload.sh`：`channel: (no channel — plain name/version)`），
  故 `manifest.yaml` 的 `conan_ref` 记为 `libtk-img/2.1.1`。

