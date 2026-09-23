# libdex 1.1.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-10
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos) / clang++
- 状态: built（本地 conan-verify 全门禁通过；PR 合入后由 CI 发布 upload）

## 编译步骤

```bash
# 1. init-build 下载官方源码（download.gnome.org）并核验 SHA-256
python3 scripts/ohc-run.py init-build libdex 1.1.0 \
  --url="https://download.gnome.org/sources/libdex/1.1/libdex-1.1.0.tar.xz"
# sha256: a9e04c8abee01c9a7cf1148c5b7aa66ba377efe6af6d83801d4fd1aa55219aaa

# 2. 本机探索编译（验证补丁与依赖方案）
meson setup builddir --prefix=$DEFAULT_PREFIX \
  -Dintrospection=disabled -Dvapi=false -Ddocs=false \
  -Dexamples=true -Dtests=true -Dliburing=disabled \
  -Dsysprof=false -Dgdbus=disabled \
  -Dc_link_args="-L<libucontext>/lib -lucontext -lucontext_posix"
ninja -C builddir            # 82/82 目标完成
DESTDIR=$TEST_PREFIX ninja -C builddir install
meson test -C builddir       # 12/12 PASS

# 3. conan-init 生成配方 → 修正依赖/补丁 → conan-verify
python3 scripts/ohc-run.py conan-init libdex 1.1.0
python3 scripts/ohc-run.py conan-verify libdex 1.1.0   # G0-G4/L2/L4/L5 全 PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson: ERROR: C shared or static library 'atomic' not found` | OHOS musl sysroot 无 libatomic（aarch64 原子操作由 clang 内建实现） | 补丁 0002-src-meson.build.patch：`host_machine.system() != 'harmonyos'` 时跳过 `cc.find_library('atomic')`（知识草稿 DRAFT-libdex-1.1.0-ohos-meson-skip-libatomic） |
| 2 | `call to undeclared function 'makecontext'/'getcontext'/'swapcontext'`（-Werror） | OHOS musl libc 的 ucontext.h 只声明 struct，不声明/不提供 ucontext 上下文切换函数 | 依赖 libucontext/1.5.2（ohpcd 已发布 OHOS 包），补丁 0001-src-dex-ucontext-private.h.patch 以配置检测守卫 `HAVE_UCONTEXT_H && !(__linux__ && __mips__)` 补充 4 个 extern 声明（R8 合规，无平台宏）；`package_info` 追加 system_libs ucontext/ucontext_posix（知识草稿 DRAFT-libdex-1.1.0-ohos-libucontext-ucontext） |
| 3 | `Dependency "gio-unix-2.0" not found`（conan create 干净构建） | glib 配方未声明 gio-unix 组件，PkgConfigDeps 不产出 gio-unix-2.0.pc | conanfile.py `_write_gio_unix_pc()` 手工写入 generators 目录（头文件在 glib 包 include/gio-unix-2.0，API 在 libgio-2.0） |
| 4 | 官方 GitLab archive 重定向登录页 | gitlab.gnome.org 匿名下载 302 | 改用官方 download.gnome.org 发布源（libdex-1.1.0.tar.xz）并核验 sha256sum |

## 源码修改

- `patches/0001-src-dex-ucontext-private.h.patch`：以配置检测守卫声明 getcontext/setcontext/swapcontext/makecontext（配合 libucontext）
- `patches/0002-src-meson.build.patch`：OHOS 平台跳过 `cc.find_library('atomic')`
- **R8 合规（修复前 → 修复后）**：R03 该补丁在 mips 分支后追加 `#if defined(__OHOS__) && defined(HAVE_UCONTEXT_H)` 平台条件宏补 4 个 extern 声明（违反 R8，审查 P1 阻塞）。R04 改为**配置检测守卫** `#if defined(HAVE_UCONTEXT_H) && !(defined(__linux__) && defined(__mips__))`（方案 A，审查方建议）：在 mips 既有分支之外的"已有 ucontext.h 且未在 mips 分支声明"的通用条件下补充 POSIX 签名 extern 声明，不依赖 `__OHOS__` 预处理宏，与 meson `host_machine.system()` 配置检测解耦；在已有声明的 libc 上为兼容重复声明。conan create 干净构建实测：ucontext 声明生效、fiber 测试可链接运行、无 -Werror=implicit-function-declaration。背景：OHOS musl libc 的 ucontext.h 只声明 struct 不提供上下文切换函数实现，由 libucontext 提供（makecontext 弱符号 + getcontext/swapcontext/setcontext 强符号），故必须显式声明（详见 DRAFT-libdex-1.1.0-ohos-libucontext-ucontext）。

## 依赖版本

- glib/2.88.3（gio-unix-2.0 >= 2.87）
- libucontext/1.5.2（仅 OHOS：ucontext 上下文切换实现）
- pcre2/10.47、libffi/3.5.2、proxy-libintl/0.5、zlib/1.3.2（glib 传递依赖）

## 验证结果

```bash
# R03（-Dgdbus=enabled，依赖线闭环后）：源码声明 75 用例/13 文件；当前配置实例化
# 13 个可执行用例，全量运行 75/75 通过（含 test-dbus 11 用例，glib/2.88.3.1 +
# dbus/1.14.10.2 提供 gdbus-codegen 与会话总线，TCP 等价路径 + ANONYMOUS +
# passwd shim 运行）
meson test -C <build-release>  # 13/13 OK, Fail 0

# HarmonyOS 专项测试（test-ohos-fiber，仅公开 API）
./builddir/test-ohos-fiber    # fiber value=42 PASSED; channel send/recv=200 PASSED

# 消费者用例（consumer_demo.c，仅公开 API）
./builddir/consumer_demo      # taskA=10 taskB=32 total=42 PASSED

# Conan 配方验证（8 道门禁）
python3 scripts/ohc-run.py conan-verify libdex 1.1.0   # G0-G4/L2/L4/L5 全 PASS
```

## 备注

- 完整测试台账见 `reports/test-report.md`（R01/R02）、`reports/test-report-r03.md`（R03）与 `reports/test-report-r04.md`（R04，P1/P3 修复后复验）；知识候选台账见 `reports/knowledge-candidate-ledger.md`
- R03 更新：test-dbus 11 用例已随依赖线闭环（glib/2.88.3.1 PR #9454 + dbus/1.14.10.2 PR #10133）实例化并实际运行 11/11 通过；R01/R02 的"11 未实例化"在 R03 台账清零
- R04 台账修正：源码声明 75，实际执行通过 74（74/75, 98.7%），1 例未实例化——test-future 的 Promise/autoptr 在 clang 工具链下被上游源码 `#if !defined(_MSC_VER) && !defined(__clang__)` 互斥编译分支排除（非失败非跳过）；当前配置可执行集合 74/74 (100%)，13/13 可执行程序全部运行 exit 0
- 运行环境恢复（仅环境恢复，不改被测代码/配置）：AF_UNIX bind 被沙箱禁止 → TCP 等价路径；TCP 无 SO_PEERCRED → ANONYMOUS 认证；musl getpwuid_r 无 /etc/passwd 记录 → LD_PRELOAD passwd shim
---

**编译结束**: 2026-09-18 16:37
**最终状态**: built
