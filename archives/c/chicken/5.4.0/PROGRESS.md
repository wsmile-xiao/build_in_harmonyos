# chicken 5.4.0 编译进度

**首次编译**: 2026-04-29（探索性，状态 partial，仅文档无 Conan 配方）
**Conan 配方固化轮次**: 2026-08-03（状态 built，conan-verify 8 道门禁通过）
**软件**: chicken 5.4.0
**构建系统**: autotools (自定义 Makefile，无 configure 脚本)
**平台**: HarmonyOS PC (aarch64)，os=OHOS，clang 15.0.4

---

## 2026-08-03 配方固化轮次步骤记录

| 步骤 | 状态 | 耗时 | 备注 |
|------|------|------|------|
| W0 依赖预检 | ✅ 通过 | ~1s | `preflight_check.sh chicken/5.4.0`：无外部依赖 |
| W1 同步 main | ✅ 完成 | ~5s | git checkout main && git pull origin main |
| init-build | ✅ 完成 | ~2min | 官方 URL，SHA256=3c5d4aa6... |
| make 编译 | ✅ 完成 | ~2m47s | `make PLATFORM=linux C_COMPILER=clang -j1`，退出码 0 |
| make install (DESTDIR) | ✅ 完成 | ~22s | 注入 install wrapper（E098/E174） |
| make check | ⚠️ 部分 | ~3min | 6377 通过 / 1 失败（E046 posix file-permissions） |
| conan-init | ✅ 完成 | ~10s | 生成 conanfile.py + conandata.yml + test_package/ |
| 人工检查配方 | ✅ 完成 | - | R26/R32/R33/R34/R38/R39 逐项核对 |
| conan-verify | ✅ PASS | ~7min | G0-G4 + L2/L4/L5 共 8 道门禁 |
| finish | ✅ 完成 | ~3min | W3 本地 CI 模拟通过，状态 built |
| W5 知识检查 | ✅ 完成 | ~10s | graph validate；无新错误模式，无需草稿 |

## 编译参数

```bash
# 编译命令（conanfile.py 固化）
make PLATFORM=linux PREFIX=$package_folder C_COMPILER=<conan conf> \
  INSTALL_PROGRAM=<install-wrapper> -j1

# 安装命令（conanfile.py package() 固化）
make install PLATFORM=linux PREFIX=$package_folder INSTALL_PROGRAM=<install-wrapper> -j1

# 测试命令（探索阶段验证）
make PLATFORM=linux PREFIX=$DEFAULT_PREFIX C_COMPILER=clang check
```

## 关键变量

- `PLATFORM`: linux (使用 Makefile.linux)
- `C_COMPILER`: clang（本机无 gcc，从 Conan conf 获取，R33）
- `INSTALL_PROGRAM`: install wrapper（E098/E174，toybox 缺 install 命令）
- `BUILD_SRC_DIR`: ~/tmp/builds/chicken-5.4.0.work
- `BUILD_ARCHIVE_DIR`: archives/c/chicken/5.4.0

## 测试结果摘要

- 通过: 6377 测试
- 失败: 1 测试 (posix-tests.scm:116 file-permissions, E046 平台限制)
- 总计: 6378 测试
- 状态: built（E046 记录为平台限制，不阻塞）

## 产物清单

### 二进制文件（9 个）
- chicken (2.7 MB) - Scheme-to-C 编译器
- csi (231 KB) - 交互式解释器
- csc (240 KB) - 编译器驱动
- chicken-install (772 KB) - egg 包管理器
- chicken-uninstall (96 KB) - egg 卸载工具
- chicken-status (121 KB) - egg 状态查询
- chicken-profile (84 KB) - 性能分析
- chicken-do (23 KB) - 构建辅助
- feathers (1.9 KB) - 调试器前端

### 库文件
- libchicken.so.11 (4.0 MB) - 动态库
- libchicken.a (7.5 MB) - 静态库
- *.import.so (43 个) - 模块导入库
- types.db - 类型数据库

### 头文件
- chicken.h
- chicken-config.h

## Conan 配方固化结果

### conan-verify 8 道门禁
| 门禁 | 名称 | 结果 |
|------|------|------|
| G0 | 预构建风险评估 | ✅ PASS |
| G1 | 配方完整性 | ✅ PASS |
| G2 | conan create（干净构建） | ✅ PASS（真实执行 + test_package 实质测试） |
| G3 | 系统同名库隔离 (R26) | ✅ PASS（chicken 非系统同名库） |
| G4 | 产物完整性 | ✅ PASS（9 bin + 2 lib + 43 import + 2 header） |
| L2 | smoke test (--version) | ✅ PASS（csi/csc/chicken 版本验证） |
| L4 | 安全扫描 (NX/PIE/RELRO) | ✅ PASS（readelf 实测 DYN+PIE+NX+RELRO） |
| L5 | 产物基线 (SHA256) | ✅ PASS（6 个关键产物记录哈希） |

### commands.json（R38）
- 位置: `archives/c/chicken/commands.json`（软件级）
- 类型: tool（9 个可执行文件）
- ref: chicken/5.4.0, binary: false（未 upload）

### 关键校验哈希
- 源码 tarball SHA256: 3c5d4aa61c1167bf6d9bf9eaf891da7630ba9f5f3c15bf09515a7039bfcdec5f
- conan create 产物（cache `~/.conan2/p/b/chickf5eb965aa73d7/p/`）：
  - bin/chicken: b0e627baf1cc83b8c5890804d456f06282174f82b173b4d9d308a5ab976c9197
  - bin/csi: 19fb068f70d3506bd2d2f55971fbe088a20a08794261f758dfec83c3434abc49
  - bin/csc: 9df8177f0bde87cfc10280fb47f4dc77ea1f3dc2d968bed69ae314427ac38695
  - lib/libchicken.so.11: c3a2d5461608b31532c020591527e112faec042a3c093367600c8bd01698f937
  - lib/libchicken.a: 9325ab935731e9d5238cf69eb5275ac7a75e1cf5d9eec37efed6cd6d0818706e

## 发现与知识

### 平台限制 (L1)

**E046: chmod 不生效**
- 现象: posix file-permissions 测试失败，期望权限 438 (0666)，实际不符
- 原因: 鸿蒙平台 SELinux 限制
- 解决: 记录为平台限制，不阻塞编译

### 编译经验 (L2)

**自定义 Makefile 构建系统**
- 特点: 不使用标准 configure，直接指定 PLATFORM
- 参数: `make PLATFORM=linux PREFIX=... C_COMPILER=clang`
- 注意: 不支持并行编译 (-j)，必须 -j1 (R9)

**E098/E174: install 命令缺失**
- 现象: `install: inaccessible or not found`
- 原因: HarmonyOS toybox 不包含 GNU coreutils 的 install 命令
- 解决: 编写 cp+chmod 语义的 install wrapper，通过 INSTALL_PROGRAM 注入 make

**R33: Conan conf 编译器获取**
- 现象: `self.conf.get("tools.build:compiler_executables:c")` 报不存在
- 原因: conf 是 dict 类型（`{"c": "...", "cpp": "..."}`），不能取子键
- 解决: `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` 再取 ["c"]

### 本版笔记 (L3)

- 无源码修改，补丁数为 0
- 预生成的 .c 文件直接可用
- 编译选项: -Os -fomit-frame-pointer -fno-strict-aliasing -fwrapv
- test_package 实质调用: csc 编译 test_hello.scm 并运行（R34）

## 问题记录

### 问题 1: posix file-permissions 测试失败 (E046)
```
Error: (posix-tests.scm:116) assertion failed:
(equal? (file-permissions "posix-tests.out") 438)
```
- 测试期望文件权限为 0666 (438)，实际因 SELinux 限制不符
- 属于鸿蒙平台已知限制，不阻塞

### 问题 2: 下载 SSL 证书验证失败 (E034/E185)
- init-build 用 urllib 下载报 SSL CERTIFICATE_VERIFY_FAILED
- 解决: 正式流程为先运行 `check-env` 安装 CA 证书（自动安装 119 个根证书），再用 HTTPS 下载 tarball 并校验 SHA256 与官方一致（探索阶段曾用禁用 TLS 校验的临时手段，已废弃，禁止复用）

### 问题 3: conan-verify G2 两次失败
- 第一次: conan conf API 使用错误（R33 dict 用法）
- 第二次: test_package 导入 `(chicken version)` 模块不存在（chicken-version 在 `(chicken platform)`）
- 均修复后通过，引擎命中 E001/E165 为误匹配（实际是配方编写问题）

## 对话记录

### Session 1 (2026-04-29): 探索性编译
1. init-build → 编译 → DESTDIR 安装 → make check → 打包 → 归档（状态 partial）
2. 产物: 9 二进制 + libchicken + 44 import 模块（无 Conan 配方）

### Session 2 (2026-08-03): Conan 配方固化
1. W0/W1 → init-build（复用官方 tarball）
2. make 编译（C_COMPILER=clang）→ DESTDIR 安装（install wrapper）→ make check（6377/1）
3. conan-init → 人工检查配方 → 修复 R33 conf 用法 → conan-verify 8 道门禁 PASS
4. commands.json（R38）→ finish（built）→ W5 知识检查

---
**首次编译**: 2026-04-29 (partial)
**Conan 配方固化**: 2026-08-03 (built)
**最终状态**: built
**归档完整**: ✅
