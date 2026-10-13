# librepo 1.18.0 — OHOS 适配笔记

## 1. 目标定位

| 项 | 值 |
|---|---|
| 任务目标 | `feat/librepo-1.18.0` → 包名 `librepo`，版本 `1.18.0`（任务 contrib-14940） |
| 上游仓库 | https://github.com/rpm-software-management/librepo |
| tag | `1.18.0` |
| 源码 URL | https://codeload.github.com/rpm-software-management/librepo/tar.gz/refs/tags/1.18.0 |
| sha256 | `c6f531df6d148d29d192f25383c13cbe0cfcbba4c8046513f0d660bbfcb9ab1b` |
| 构建系统 | CMake（`cmake_minimum_required(2.8.5...3.26)`，cmake 4.x 需 `CMAKE_POLICY_VERSION_MINIMUM=3.5`） |
| 产物 | `lib/librepo.so`（OUTPUT_NAME=repo，平铺 SONAME=librepo.so）+ `include/librepo/*.h` + `librepo.pc` |
| 语言 | C |

## 2. 依赖（全部制品仓已发布）

| 依赖 | 版本 | 发现方式 | 备注 |
|---|---|---|---|
| glib | 2.84.0.1 | PKG_CHECK_MODULES(glib-2.0>=2.66, gio-2.0) | PkgConfigDeps |
| curl | 8.15.0.1 | FIND_PACKAGE(CURL) | 预置 CURL_LIBRARY/CURL_INCLUDE_DIR 缓存变量（无 gpgme-config 问题，但避免系统搜索）；与 zchunk 的传递依赖对齐 |
| openssl | 3.5.6.1 | PKG_SEARCH_MODULE(libcrypto openssl) | 命中 openssl.pc（第二候选） |
| libxml2 | 2.15.3.1 | PKG_CHECK_MODULES(libxml-2.0) | 上游未把 *_INCLUDE_DIRS 入 INCLUDE_DIRECTORIES → 补丁 |
| gpgme | 1.24.0 | FIND_PACKAGE(Gpgme)（自带 KDE 版 FindGpgme，依赖 gpgme-config） | 预置 GPGME_INCLUDES/GPGME_VANILLA_LIBRARIES 走其 "cached" 分支绕过 gpgme-config（E433 族） |
| zchunk | 1.5.2 | PKG_CHECK_MODULES(zck>=0.9.11) | 上游未入 INCLUDE/LINK → 补丁 |
| check | 0.15.2 | PKG_CHECK_MODULES(check)（仅测试链接） | 上游把 INCLUDE_DIRECTORIES 注释掉了 → 补丁 |

## 3. 上游测试口径

- **START_TEST 总数 = 55**（取数：`grep -c START_TEST tests/test_*.c | awk -F: '{s+=$2} END {print s}'`）。
  分布：checksum 4 / downloader 6 / gpg 3 / handle 2 / lrmirrorlist 4 / metalink 10 /
  mirrorlist 4 / package_downloader 1 / repoconf 3 / repomd 1 / repo_zck 1 /
  url_substitution 4 / util 11 / version 1。
- **无网络默认执行 48**（12 个 suite；downloader 6 例仅 `-d`（需互联网）注册；
  repo_zck 1 例上游编译但未 `srunner_add_suite`）。
- 运行方式：`build()` 内逐 suite `CK_RUN_SUITE=<name> ./tests/test_main tests/test_data/`
  （`LD_LIBRARY_PATH` 注入依赖 libdirs + 构建树 librepo/）。

## 4. 适配改动（单补丁 0001-ohos-build-adjustments.patch）

1. **CMakeLists（顶层）**：`GPGME_INCLUDES`/`ZCHUNKLIB_INCLUDE_DIRS` 补入
   INCLUDE_DIRECTORIES（conan 非系统前缀，上游假设 /usr/include）；
   `LINK_DIRECTORIES(GLIB2/LIBXML2/LIBCRYPTO/ZCHUNKLIB 的 *_LIBRARY_DIRS)`
   ——否则 `-lxml2/-lglib-2.0/-lzck/...` 链接期全部找不到。
2. **librepo/CMakeLists**：显式 `-Wl,-soname,librepo.so`。CMake 不认识
   HarmonyOS（无 Platform/HarmonyOS.cmake、探测不到
   CMAKE_SHARED_LIBRARY_SONAME_C_FLAG）→ 默认无 SONAME → 依赖方 DT_NEEDED 记成
   链接期相对路径 `../librepo/librepo.so`，运行期只按 CWD 解析（LD_LIBRARY_PATH
   无效）。平铺 SONAME 后 DT_NEEDED=librepo.so 可正常解析（该族已有
   DRAFT-cmake-harmonyos-platform-soname-flag/DRAFT-E577 覆盖）。
3. **tests/CMakeLists**：补 `INCLUDE_DIRECTORIES(${LIBCHECK_INCLUDE_DIRS})`
   （上游注释掉了）。
4. **tests/test_main.c**：scratch 目录 `/tmp/librepoXXXXXX` →
   `g_build_filename(g_get_tmp_dir(), ...)`（OHOS /tmp 只读，E002 族）。
5. **tests/test_repoconf.c**：`char tmpfn[]="/tmp/librepo_repoconf_test_XXXXXX"`
   → 运行期用 `g_get_tmp_dir()` 组模板（同上）。

配方侧（非补丁）：
- `CMAKE_POLICY_VERSION_MINIMUM=3.5`（cmake 4.4.3 × 上游 2.8.5 下限）；
- `ENABLE_PYTHON/DOCS/EXAMPLES/SELINUX=OFF`（无 python 绑定/文档/示例/libselinux）；
- CURL/GPGME 缓存变量预置（见上表）；
- `package()` 后按 **E077** 四步重签 `lib/*.so*`（llvm-objcopy 去 .codesign →
  binary-sign-tool 自签 → chmod 0755）——cmake --install 改写 DT_RUNPATH 会使
  lld 写入的 .codesign 失效，消费者 dlopen 会被拒。

## 5. 上游测试实测（OHOS 真机，2026-10-08，~/​.librepo_evidence.log，RC=0）

| suite | checks | 结果 |
|---|---|---|
| checksum | 4 | 100% |
| handle | 2 | 100% |
| internal_mirrorlist | 4 | 100% |
| metalink | 10 | 100% |
| mirrorlist | 4 | 100% |
| package_downloader | 1 | 100% |
| repoconf | 3 | 100% |
| repomd | 1 | 100% |
| url_substitution | 4 | 100% |
| util | 11 | 100% |
| version | 1 | 100% |
| **小计（11 suite）** | **45** | **100%** |
| gpg | 3 | 0%（技术原因豁免，见下） |

**gpg suite 3 例未通过的技术原因**（`-v` 实测原文）：
```
DEBUG lr_gpg_context_init: gpgme_engine_check_version: Invalid crypto engine
DEBUG Failed to create "/run/user/20020085": 2 - No such file or directory
```
OHOS 无 gpg OpenPGP 运行引擎（gpgme 报 "Invalid crypto engine"；`gpg/gpgconf`
在真机与 CI 均不存在，`/run/user` 亦无）。制品仓虽有 gnupg/2.4.9.1、2.5.22
配方，但其依赖链 libgcrypt/1.12.2、libksba/1.6.7.1、npth/1.8 **均无预编译
二进制**，本 PR 范围内无法引入真实 gpg 运行时；库的链接与 API 均正常
（gpg_gpgme.c 编译链接全过），仅运行期引擎缺失导致 3 例校验用例无法执行。
downloader 6 例需 `-d`（真实互联网），未运行；repo_zck 1 例上游未注册进
runner（上游 1.18.0 事实，非适配省略）。

## 6. 消费者测试（test_package，17/17）

`test_consumer.c` 链接安装后的 `librepo.so`（重签后 dlopen 正常），本地解析
metalink3 fixture（上游 metalink_good_01 同格式裁剪版）断言
filename/timestamp/size/hash×2/url×2 等 15 项 + LR_VERSION_CHECK 宏 2 项：
`ALL 17 CHECKS PASSED`。

## 7. 路径 B（知识库扩展，issue #3861）

本库适配实测踩到、且 KB 查重（2026-10-08，`node tools/kb-check.mjs`）**0 命中**的新族：

**pkg-config「发现 ≠ 消费」消费层缺口**：`PKG_CHECK_MODULES(<P> <mod>)` 成功只代表
「发现」（产出 `_INCLUDE_DIRS/_LIBRARY_DIRS/_LIBRARIES` 三组变量）；上游 CMake 在
Linux 单前缀世界养成的习惯是只拿 `_LIBRARIES` 链接、从不接线另外两组——conan
非系统前缀下编译（`'zck.h'/'check.h' file not found`）与链接（`ld.lld: unable to
find library -lxml2/-lgio-2.0/-lzck/...`）双炸，而 configure 全绿。

- 查重：`LIBRARY_DIRS` 0 / `zck.h` 0 / `unable to find` 0；四邻居子族
  （E075 环境陷阱、E468/E348 发现层、E537 记录层）判别树与分流探针写在草稿里
- 通用性：main 已合入 ≥8 个配方各自手搓同一补丁（ciftilib/ayatana×4/avro-c/
  jshn/blur/cassiopee/rcon/ustream-ssl）——高发而图谱无条目；本库单库 4 处实例
- 实测证伪：修复前后完整日志（编译/链接错误原文 vs RC=0 + 45/48 + 17/17）

草稿：`knowledge/drafts/DRAFT-ohos-pkgconfig-consumption-gap-include-library-dirs.{kv,md}`
（`draft: true`、`contributor_id: frj__`）。关联 issue **#3861**。

另一疑似候选「libcheck IPC 临时文件优先级反转」（TEMP > P_tmpdir 只读 /tmp >
TMPDIR）经按框架名 `libcheck` 重查，已被 main 的 DRAFT-E547/E571/libdsme 覆盖
（初查只用机制词 `P_tmpdir` 漏检——查重必须含框架名）；配方中保留 `TEMP` 注入
并引用上述条目。其余坑族同样已有条目（E433 gpgme-config、E077 重签、
DRAFT-cmake-harmonyos-platform-soname-flag/E577 soname、E002 /tmp）。

## 8. 复现

```sh
conan create archives/l/librepo/1.18.0 \
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 -pr:b=$HOME/.conan2/profiles/ohos-aarch64 \
  --build=missing
# 上游测试在 build() 内自动执行；完整证据日志另存（45/45 + gpg 3 例技术原因 + 消费者 17/17）
```
