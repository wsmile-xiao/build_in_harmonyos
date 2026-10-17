# libidl2 0.8.14 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，2010 年生成的 configure 脚本）
- 编译日期: 2026-09-18
- 编译器: clang（macOS 本地验证 apple-clang 17；OHOS CI: /data/service/hnp/bin/clang 15, aarch64-linux-ohos）
- 状态: built（本地 macOS 原生验证通过；OHOS 真机/CI 验证待远程执行）

## 编译步骤

源码来自官方发布 tarball（GNOME libIDL 0.8.14，SHA256 见 manifest/conandata）。

1. 依赖：glib-2.0 >= 2.4.0（configure.in: PKG_CHECK_MODULES(LIBIDL, glib-2.0)），
   由 Conan 提供（glib/2.84.0.1 → libffi/pcre2/zlib 链）。
2. 构建工具：flex（AM_PROG_LEX 硬性要求）+ bison/yacc（AC_PROG_YACC）。
   OHOS CI 无系统 flex/bison，配方对 OHOS 平台注入 tool_requires flex/2.6.4 + bison/3.8.2；
   macOS 本地验证用系统 flex 2.6.4 / bison 2.3。
3. macOS 本地原生验证（G0 干净构建，CONFIG_SHELL=/bin/bash 覆盖 OHOS worker shell 路径）：
   ```bash
   ./configure --prefix=... --enable-static --disable-shared
   make -j1          # libIDL-2.la + tstidl 编译成功（仅 1 个 unused-but-set 警告）
   make install      # 1 bin（libIDL-config-2）+ 5 lib 产物正常
   ./tstidl test-basic.idl   # 上游测试运行：解析成功、repo id/常量/标识符/树还原输出正确
   ```
4. 配方验证：conan export（配方+conandata+补丁导出成功）；conan graph info 依赖解析正常。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 2008 版 config.sub 不识别 aarch64-linux-ohos triplet | 上游 config.sub/config.guess 过于陈旧（CPU 无 aarch64、OS 无 ohos） | 打补丁 0001-config.sub-ohos.patch：OS 族加 linux-ohos*、CPU 加 aarch64、后缀加 -linux-ohos*；OHOS 构建显式传 --build/--host=aarch64-linux-ohos；已用 config.sub 实测识别 + 回归测试 |
| 2 | configure 硬性要求 flex/yacc | AM_PROG_LEX 非 flex 即报错 | OHOS 平台 tool_requires flex/2.6.4 + bison/3.8.2（CI 无系统版本）；本地 macOS 用系统版本 |
| 3 | 本机 macOS 无法完成 OHOS conan create | 本机为 macOS 开发机，无 OHOS SDK/工具链（/data/service/hnp 路径不存在，SDK 需华为账号下载）；native 依赖链 libffi 3.4.4 的 aarch64 sysv.S 使用 GNU CFI 语法，Apple 集成/独立汇编器均报 invalid CFI advance_loc expression | 本地验证做到：源码级编译 + 上游测试运行 + G0 干净构建 + 配方导出/依赖解析（全部通过）；OHOS 真机交叉验证依赖远程 CI（PR 触发，CI 使用 ohpcd 制品仓的 OHOS 预编译 glib/libffi/pcre2/zlib 二进制，无需本机构建）——未伪造任何结果 |
| 4 | libIDL-config-2 bin 脚本会触发 CLI 包判定 | 过时 config helper（被 pkg-config 取代） | package() 中删除该脚本与 .la 文件 |

## 源码修改

- patches/0001-config.sub-ohos.patch：config.sub 增加 linux-ohos OS 族、aarch64 CPU、-linux-ohos 后缀识别（参照 aalib 先例）

## 依赖版本

- glib/2.84.0.1（Conan，OHOS CI 用制品仓预编译二进制；依赖链 libffi/3.4.4 + pcre2/10.45 + zlib/1.3.1.1）
- 构建工具：flex/2.6.4、bison/3.8.2（OHOS tool_requires）；macOS 本地用系统 flex 2.6.4/bison 2.3

## 验证结果

```bash
# macOS 本地（原生）：
# 1) G0 干净构建：configure + make + make install 全部成功（clean-verify）
# 2) 上游测试 tstidl：解析 IDL 成功，输出 repo id IDL:Test/Hello:1.0、常量、标识符、树还原（1/1 通过）
# 3) conan export + graph info：配方/依赖解析通过
# OHOS 平台验证：待远程 CI（本机无 OHOS 工具链）
```

## 注意事项

- W3 本地 CI 模拟（conan create OHOS profile）在本机受环境限制无法执行：
  本机无 /data/service/hnp OHOS 工具链，且 native 依赖链 libffi 在 Apple 汇编器上无法构建。
  此限制已记录，不伪造 .ci-result.json；OHOS 验证由远程 CI（PR pipeline）完成。
- 上游无 make check 目标，唯一测试程序为 tstidl（noinst_PROGRAMS）；消费者验证由
  test_package/test.c 实质调用 IDL_parse_filename / IDL_tree_walk_in_order / IDL_tree_to_IDL 完成，
  OHOS 构建时 test.c 同时验证 __OHOS__ 平台宏（rule12 鸿蒙特有测试 N=1）。

## CI 修复记录（PR #10977 第一轮失败 → 修复）

### CI 失败现象（worker OpenHarmonyPCDeveloper-CI-012，conan-build-test 步骤）
- configure 全部探测通过，但在生成 config.status 时失败：
  `config.status 报错 could not setup config files machinery`（临时 awk 脚本 subs1.awk 权限被拒，Permission denied）
- 本地 W3（ohos-local 交叉模拟）绿、CI 红——环境语义不可迁移：HMDFS 特有故障，APFS 无法复现。

### 根因（知识库 E129，与 a52dec 同源先例）
- HMDFS 对新建目录总是置 setgid 位；configure 的 config.status 临时目录用
  `(umask 077 && mktemp -d ./confXXXXXX)` 创建 → 目录权限 drwx--S---，
  连属主都无法在目录内读写文件 → subs1.awk/subs.awk 读写被拒。

### 修复
- 新增 patches/0003-configure-umask-022.patch（E129 推荐方案 + a52dec/0.7.4 先例）：
  configure 中 config.status 临时目录创建的两处 `umask 077` → `umask 022`。
- 补丁基于「原始 tarball + 0001 + 0002」后的 configure 生成（0002 在其前删 5 行，
  直接按原始行号生成的 hunk 无法应用，已按 conan 顺序应用验证）。
- conandata.yml 注册 0003（patch_type: portability）。

### 复验
- 本地 W3 复跑：三个补丁顺序应用通过 → conan create（ohos-local profile）全绿，
  L0/L1/L4/L5 全部通过，test_package 消费者验证通过。

### CI 第二轮（#51106，worker CI-011）：fork EAGAIN，判定为环境资源问题
- 现象：补丁 0003 已成功应用（config.status 权限错误消失），但 configure 启动即报
  `can't fork - try again`（configure[169] 是 autoconf 的 shell 函数探测，`(eval ...)`
  子 shell fork 失败）→ `No shell found that supports shell functions`，32s 即失败。
- 判定：**环境资源问题，非配方缺陷**（E491 回退方案口径；cpluff 真机同源经验）。
  证据：①第一轮同配方在 CI-012 上 configure 全程通过（差异只在 worker/负载）；
  ②失败点在 configure 第 169 行（shell 函数探测），与补丁改动区（15314 行）无关；
  ③fork EAGAIN = 进程表/内存压力，受限 runner 并发构建时的已知现象。
- 处置：配方不动，重新触发 CI（换 worker/低负载时刻重跑）。

### CI 第三轮（#53528，worker CI-032）：test_package 运行期 /tmp 只读 → 修复 test.c
- 现象：configure/make/install/打包/测试编译全部通过（修复链首次完整跑通），仅
  test_package 执行时 `fopen: Read-only file system`（rc=2）。测试二进制打印
  `__OHOS__ is defined` 与 `libIDL version: 0.8.14` 后，写临时 IDL 文件失败。
- 根因：test.c 硬编码 `/tmp/libidl2_test_basic.idl`；OHOS CI worker 的 /tmp 是只读
  erofs（CI 自带诊断"OHOS 文件系统只读"确认；cpluff 真机同源经验）。
- 修复（不改测试口径）：test.c 改优先写 `$TMPDIR/libidl2_test_basic.idl`，TMPDIR 缺失
  或打开失败时回退构建目录（cwd，必然可写）下的同名文件；解析/断言逻辑不变。
- 复验：本地 W3 全绿（L0/L1/L2/L4/L5，100%）。
---

**编译结束**: 2026-09-19 13:10
**最终状态**: built
