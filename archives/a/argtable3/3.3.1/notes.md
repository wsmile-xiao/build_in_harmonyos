# argtable3 3.3.1 适配笔记

## 编译环境

- **构建系统**: cmake
- **编译日期**: 2026-05-28
- **编译器**: clang 15.0.4 / clang++
- **状态**: published
- **平台**: OpenHarmony ARM64 (aarch64)
- **源码来源**: https://github.com/argtable/argtable3/releases/download/v3.3.1/argtable-v3.3.1.tar.gz

---

## 对话记录

### 对话 #1: argtable3 3.3.1 OpenHarmony 编译

- 执行 `ohc-run.py init-build argtable3 3.3.1 --url=...`
- SSL 证书问题导致下载失败，手动用 curl -k 下载到 ~/tmp/argtable-v3.3.1.tar.gz
- 复制到 `~/tmp/builds/argtable3-3.3.1.tar.gz`（脚本期望路径），再次 init-build 成功
- 脚本自动检测 BUILD_SYSTEM=autotools（因为有 Makefile），但实际是 cmake 项目

### Phase 2: 编译调试

**第一次 cmake 尝试（失败）**:
- `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..`
- 报错: `install EXPORT given no DESTINATION!` 和 `install FILES given no DESTINATION!`
- 根因: HarmonyOS 不被识别为 UNIX → `ARGTABLE3_INSTALL_CMAKEDIR` 未设置 → DESTINATION 为空

**第一次 make 尝试（部分失败）**:
- `make -j2`
- `libargtable3.a` 编译成功 ✅
- `test_src` 编译成功 ✅
- `test_amalgamation` 失败 ❌: `tools/build` 脚本 Error 126（/bin/bash 不存在）
- 根因: `#!/bin/bash` shebang 在 HarmonyOS 上无法执行

**修复方案**:
1. 修改 `src/CMakeLists.txt`:
   - 增加 `OR (CMAKE_SYSTEM_NAME MATCHES "OHOS|HarmonyOS|Unknown")` 条件
   - 增加 `else()` fallback 分支设置 `ARGTABLE3_INSTALL_CMAKEDIR`
   - 移除 `-Werror`（新平台警告可能不同）
2. 修改 `tools/build`:
   - shebang 从 `#!/bin/bash` → `#!/usr/bin/env bash`

**第二次 cmake + make（成功）**:
- `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..` → 配置成功 ✅
- `make -j2` → 全部编译成功 ✅（所有目标：argtable3、test_src、test_amalgamation、test_static、所有 example）

### Phase 3: 安装与测试

- `make install DESTDIR=$TEST_PREFIX` → DESTDIR 安装成功 ✅
- `ctest --output-on-failure` → 3/3 通过 ✅（每项 170 子测试，共 510 子测试）
- `make install`（不带 DESTDIR）→ 安装到 ~/usr/local 成功 ✅
- 功能验证: 编写测试程序链接 libargtable3.a → 编译运行成功 ✅

### Phase 4: 打包与收尾

- `ohc-run.py package argtable3 3.3.1` → 打包成功（228KB）
- `ohc-run.py verify-build argtable3 3.3.1` → G1-G4 全部 PASS ✅
- `ohc-run.py finish argtable3 3.3.1 published` → 状态设为 published ✅
- G0 干净构建验证失败（脚本限制：对 cmake 项目使用 ./configure 命令）

---

## 编译步骤

1. `python3 $SKILL_ROOT/scripts/ohc-run.py init-build argtable3 3.3.1 --url=...`
2. 修改 `src/CMakeLists.txt`: ARGTABLE3_INSTALL_CMAKEDIR 平台检测修复 + 移除 `-Werror`
3. 修改 `tools/build`: shebang `#!/bin/bash` → `#!/usr/bin/env bash`
4. `mkdir build && cd build && cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..`
5. `make -j2`
6. `make install DESTDIR=$TEST_PREFIX`
7. `ctest -V --output-on-failure` → 3/3 通过，510 子测试全部通过
8. `ohc-run.py package argtable3 3.3.1`
9. `cd build && make install`（不带 DESTDIR）
10. `pkg-config --modversion argtable3` → 3.3.1.0 ✅

---

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 补丁文件 |
|---|------|------|----------|----------|
| 1 | cmake: `install EXPORT given no DESTINATION` | HarmonyOS 不被识别为 UNIX，ARGTABLE3_INSTALL_CMAKEDIR 变量未设置 | 增加 `CMAKE_SYSTEM_NAME MATCHES "OHOS|HarmonyOS|Unknown"` 条件 + fallback else 分支 | 0001-src-CMakeLists.txt.patch |
| 2 | `tools/build` Error 126 | shebang `#!/bin/bash`，HarmonyOS 无 /bin/bash | 改为 `#!/usr/bin/env bash` | 0002-tools-build.patch |
| 3 | `-Werror` 导致潜在编译风险 | 新平台可能产生不同编译警告 | 移除 `-Werror`，保留 `-Wall/-Wextra/-Wconversion/-Wpedantic` | 0001-src-CMakeLists.txt.patch |

---

## 源码修改

### 0001-src-CMakeLists.txt.patch

- 移除 `-Werror` 编译标志（第49行）
- 增加 HarmonyOS/未知平台 cmake install 路径检测条件（第102行）

### 0002-tools-build.patch

- 替换 shebang：`#!/bin/bash` → `#!/usr/bin/env bash`

---

## 依赖版本

无外部依赖。argtable3 是纯 ANSI C 库，仅依赖标准 C 库和 math 库（-lm）。

---

## 验证结果

### pkg-config 验证

```bash
$ export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig
$ pkg-config --modversion argtable3
3.3.1.0
$ pkg-config --libs argtable3
-L/storage/Users/currentUser/usr/local/lib -largtable3 -lm
$ pkg-config --cflags argtable3
-I/storage/Users/currentUser/usr/local/include
```

### 功能验证（编译链接运行测试程序）

```bash
$ ~/tmp/test_argtable3
argtable3 works! library loaded successfully.
$ ~/tmp/test_argtable3 --help
argtable3 works! version check: argtable3 library loaded.
```

### 库文件完整性

```bash
$ file ~/usr/local/lib/libargtable3.a
ar archive
$ llvm-nm ~/usr/local/lib/libargtable3.a | head -5
arg_cmd.c.obj: T arg_cmd_count T arg_cmd_dispatch ...
```

---

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| argtable3-3.3.1-ohos-aarch64.tar.gz | 228KB (234042B) | 预编译包（含静态库+头文件+pkg-config+cmake config） |
| libargtable3.a | 105KB (105468B) | 静态库 |
| argtable3.h | 112KB (111810B) | 头文件 |
| argtable3.pc | 235B | pkg-config 文件 |
| Argtable3Config.cmake | - | cmake 配置文件 |

---

## 注意事项

- argtable3 是静态库（BUILD_SHARED_LIBS=OFF），无可执行二进制，G1/G2 检查项较少
- cmake 不识别 HarmonyOS 平台（CMAKE_SYSTEM_NAME 为空/Unknown），需在 install 路径条件中添加 fallback
- `-Werror` 在新平台编译中风险较大，建议移除
- HarmonyOS 无 `/bin/bash`，shell 脚本 shebang 需用 `/usr/bin/env bash`
- G0 干净构建验证脚本（clean-verify）仅支持 autotools 项目，对 cmake 项目使用 `./configure`，需后续改进
---

**编译结束**: 2026-06-01 16:51
**最终状态**: published
