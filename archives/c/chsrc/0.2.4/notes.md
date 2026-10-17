# chsrc 0.2.4 — 适配笔记

## 基本信息
- 软件: chsrc (全平台换源工具)
- 版本: 0.2.4
- 语言: C
- 构建系统: Makefile (非 autotools)
- 编译日期: 2026-05-26

## 构建系统分析
chsrc 使用纯 Makefile 构建，无 configure 脚本。
- 编译: `make build-in-release-mode`
- 安装: `make install` (原 Makefile 使用 /usr 硬编码路径)
- 测试: `make test` (test-xy, test-fw)

## 源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| `src/framework/core.c:1455` | `/tmp` 硬编码，HarmonyOS /tmp 为只读 erofs (PSCAN-FS-001) | 改用 `getenv("TMPDIR")` + fallback `/tmp` | 待 refresh-patch |
| `lib/xy.h:1341-1354` | OS 检测不识别 HarmonyOS (`_xy_detect_os()` 抛 "Unknown operating system") | 添加 `#ifdef __OHOS__` 编译时守卫 + `uname -s` 运行时 "HarmonyOS" 检测 | 待 refresh-patch |
| `Makefile:install target` | 原 install 使用 `$(DESTDIR)/usr/bin/chsrc` 硬编码路径，不符合 DESTDIR+PREFIX 模式 (R20) | 添加 `PREFIX ?= /usr/local` 变量，改 install target 为 `$(DESTDIR)$(PREFIX)/bin/chsrc` | 待 refresh-patch |

## 编译过程

### 构建命令
```bash
# 构建
cd $BUILD_SRC_DIR
make build-in-release-mode PREFIX=$DEFAULT_PREFIX CC=clang \
  CFLAGS="-Iinclude -Ilib -fPIC -O2 -D__OHOS__ -Wall -Wextra -Wno-unused-variable ..."

# 安装 (DESTDIR 模式 R20)
make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX

# 测试
make test-xy  # PASS: xy.h 测试全部通过
make test-fw  # PASS: Frameworker test pass!
```

### 关键修复说明

1. **HarmonyOS OS 检测** (`lib/xy.h`)
   - `/proc/version` 在 HarmonyOS 上无法读取 (Permission denied)
   - `uname -s` 返回 "HarmonyOS" (非 "Linux")
   - 修复: 在 Linux 检测前添加 `#ifdef __OHOS__` 编译时分支，并在 `uname` 检测中添加 "HarmonyOS" 运行时识别
   - 设计: 设置 `xy.on_linux=true` (HarmonyOS 是 Linux-like 系统)

2. **临时文件路径** (`src/framework/core.c`)
   - 原代码硬编码 `/tmp/chsrc_tmp_...`
   - HarmonyOS 上 `/tmp` 为只读 erofs
   - 修复: 使用 `getenv("TMPDIR")`，fallback `/tmp`
   - 测试确认: test-fw 中临时文件正确使用 `$TMPDIR`

3. **Makefile PREFIX/DESTDIR** (`Makefile`)
   - 原 install: `install -D -m 755 chsrc-release $(DESTDIR)/usr/bin/chsrc`
   - 问题: 不支持 PREFIX 变量，路径硬编码为 /usr
   - 修复: 添加 `PREFIX ?= /usr/local`，改 install target 使用 `$(DESTDIR)$(PREFIX)/bin/chsrc`
   - 注意: 使用 `install -d` + `install -m` 分步（原 `install -D` 在 HarmonyOS 上可能有问题）

## 测试结果
- test-make-env: PASS
- test-xy: PASS (xy.h 测试全部通过)
- test-fw: PASS (Frameworker test pass!)
- `chsrc --version`: 正确输出 "chsrc v0.2.4 (2025/12/31)"

## /etc/ 硬编码说明
预编译扫描发现大量 `/etc/` 硬编码路径。这些是 chsrc 作为换源工具的功能性路径（读取/修改各发行版包管理器配置），不是构建问题，不需要修改。---

**编译结束**: 2026-05-26 06:26
**最终状态**: built
---

**编译结束**: 2026-05-26 06:29
**最终状态**: built

---

## 2026-07-25 conan create 本地验证

| 检查项 | 结果 | 说明 |
|--------|------|------|
| `conan export` 配方导出 | ✅ 通过 | 配方语法正确 |
| 补丁应用（3/4 个） | ✅ 通过 | 去除 `0002-configure.patch`（创建新文件，非必需） |
| `make build-in-release-mode` | ✅ 通过 | 编译成功，输出 chsrc-release 二进制 |
| `package()` 打包 | ✅ 通过 | 打包 chsrc 二进制 + chsrc.1 man 手册 |
| `test_package` — 执行 `chsrc --version` | ✅ 通过 | 输出 "chsrc v0.2.4 (2025/12/31)" |
| **断言通过率** | **2/2（100%）** | chsrc --version 退出码 0 + 版本号正确 |
