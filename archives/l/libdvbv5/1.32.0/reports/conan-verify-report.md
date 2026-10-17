# Conan Verify Report — libdvbv5 1.32.0

**Verdict**: PASS
**Reference**: `libdvbv5/1.32.0@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-09-22T10:35:20.521176

> **人工校注（G0 构建系统误判，非本次产物问题）**
> 下方 G0 段落显示 `📦 构建系统: autotools` 并据此命中 E490（autotools 脚本
> 执行位），**该判定有误**：本配方为 **Meson**（实际以 `MesonToolchain` +
> `Meson(self).configure()/build()/install()` 构建，`manifest.yaml`
> 亦声明 `build_system: meson`）。
>
> 误判根因：`scripts/ohc/conan_verify.py::_detect_build_system_from_conanfile`
> 的判定顺序为 cmake → **autotools** → meson，命中条件为子串
> `from conan.tools.gnu import`。本配方为生成依赖的 `libudev.pc` 而引入
> `from conan.tools.gnu import PkgConfigDeps`，因此先命中 autotools 分支。
> 属框架检测规则与「Meson 项目使用 PkgConfigDeps」这一常见组合的冲突，
> **本次不改动框架文件**（W2：框架修改须独立 PR）。
>
> 影响评估：无。E490 是 autotools 专有风险（`configure`/`config.guess`
> 执行位），对 Meson 构建不适用；G0 为非阻断门禁，且 G2 已实际
> `conan create` 成功（退出码 0），证明该风险不存在。

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
  ✅ R26: 系统同名库静态链接配置存在
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)
  ✅ test_package/MANIFEST.yml 存在

## G2: ✅ PASS
  ✅ conan create 成功
  📄 日志: archives/l/libdvbv5/1.32.0/reports/conan-create.log

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

> **人工校注（L2/L4/L5 的实际结果）**
> 本节 L2/L4/L5 显示「跳过（无 cache 路径）」，原因是本次 `conan-verify`
> 未能解析出已构建包的 cache 路径（`_cache_path` 为空），因此这三道检查
> 在**本次 conan-verify 进程内**未执行，并非「无可检产物」。
>
> 该限制不影响验收：W3 本地 CI 模拟（`reports/w3-local-ci.log`）在
> 同一台机器上成功解析到包并**实际执行**了这三道检查，实测结果：
>
> | 检查 | W3 实测结果 |
> |---|---|
> | L2 | `L2_RESULT=skip: no bin/ dir`（纯库包，无 `bin/`，符合预期） |
> | L4 | `L4_RESULT=pass: patches clean` |
> | L5 | `L5_RESULT=pass: lib/ has content` |
>
> 另：本包为纯库包，无 `bin/` 目录，故 L2 smoke test 按设计跳过。
> 完整 W3 结果见 `reports/test-report.md` 第 5 节。
