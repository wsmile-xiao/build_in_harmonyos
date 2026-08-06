# Data-UUID 1.227 测试报告

## 测试概况

**测试日期**: 2026-08-06
**编译系统**: Perl ExtUtils::MakeMaker (Makefile.PL) + Clang 15.0.4
**测试平台**: OpenHarmony aarch64-linux-ohos
**Perl 版本**: 5.42.0
**总测试数**: 32 (across 4 test files, excluding skipped)
**通过率**: N/A — 测试因平台限制无法加载 .so (E212)

## 编译验证

### 编译阶段 ✓

- **UUID.xs → UUID.c**: xsubpp 生成成功
- **UUID.c → UUID.o**: clang 编译通过 (1 warning: gethostid 已修复)
- **UUID.o → UUID.so**: 链接成功，生成 35KB 共享库
- **ELF 验证**: AArch64 shared object, 64-bit LSB

### 适配修改

- **UUID.xs**: 添加 `__OHOS__` 守卫，跳过 `gethostid()` 调用 (OHOS 平台不可用, E051-class)

## 测试套件执行详情

### t/basic.t (28 tests)

**状态**: ✗ 无法执行 — 模块加载被 SELinux 阻止
**原因**: HMDFS 文件系统上的 .so 文件无法 dlopen (E212, hmmac 安全标签)
**详情**: `Can't load '...UUID.so' for module Data::UUID: Permission denied`

### t/from-name-collisions.t (1 test)

**状态**: ✗ 无法执行 — 同上 SELinux 限制

### t/leaky_dollar_bang.t (1 test)

**状态**: ✗ 无法执行 — 同上 SELinux 限制

### t/segv.t (2 tests)

**状态**: ✗ 无法执行 — 同上 SELinux 限制

### t/pod-coverage.t

**状态**: ⏭ Skipped — 需设置 $ENV{AUTHOR_TESTING}

### t/pod.t

**状态**: ⏭ Skipped — 需设置 $ENV{AUTHOR_TESTING}

### t/threads.t

**状态**: ⏭ Skipped — Perl 未编译 ithreads 支持

## 平台限制说明

OpenHarmony 的 hmmac (Harmony MAC) 安全模块根据文件路径分配安全标签：
- `/data/service/hnp/` 下的文件获得 `hnp_file` 标签 → 可 dlopen
- `/storage/Users/` (HMDFS) 上的文件获得 `hmdfs` 标签 → Permission denied

Perl 解释器运行在 `hnp_file` 安全上下文，仅允许加载 `hnp_file` 标签的 .so 文件。
用户无权写入 `/data/service/hnp/`，导致编译产物无法在测试阶段被 dlopen 加载。

**解决方案**: 通过 cmd-pkgs HNP 包安装到 `/data/service/hnp/` 目录获得正确安全标签。

## Conan 验证 (conan-verify)

- **G1 配方完整性**: ✓ PASS
- **G2 conan create**: ✓ PASS (干净构建成功，test_package 通过)
- **G3 系统同名库隔离**: ✓ PASS
- **G4 产物完整性**: ✓ PASS

## 结论

编译和打包验证全部通过。运行时测试因 OHOS HMDFS SELinux 限制 (E212) 无法执行，
这是已知的平台限制，非构建缺陷。通过 Conan test_package 验证包内容完整性。
