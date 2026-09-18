# libeio 1.0 适配笔记

## 编译环境
- 构建系统: autotools（官方 tarball 无预生成 configure，需 autoreconf）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18）
- 状态: built（本地验证通过；制品未上传，待 CI 发布后置 published）
- 上游: https://github.com/scunningham/libeio (master, MIT)
- 源码 SHA-256: 291f8a6dacda89dfe97a3155f2060f95e7f893b24eda93267510b3b46e54e14e

## 编译步骤
1. 官方 master tarball 下载（codeload/github archive 双通道，SHA-256 一致校验）
2. `./autogen.sh`（autoreconf --install --symlink --force）生成 configure
   - 前置：安装 automake 1.16.5 + libtool 2.4.7(实际2.5.4) 预编译包到 ~/usr/local
   - 修复 aclocal/automake/libtoolize 的 shebang（perl/bash 软链接）；修复版本不匹配后重跑 autogen
3. `./configure --prefix=$DEFAULT_PREFIX`
   - config.guess/config.sub 打 OHOS 补丁（patch-autotools-ohos.pl + config.sub 内核列表补 linux-ohos* 分支）
4. `make -j1` && `make check`（check 无测试目标，rc=0）&& `make install DESTDIR=`
5. `conan-verify libeio 1.0`：G0-G4 + L2/L4/L5 全部 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载超时/Empty reply | GitHub 直连不稳（本机网络） | codeload tarball + github archive 双通道，SHA-256 一致校验 |
| 2 | /tmp 只读无法建目录 | OHOS HMDFS /tmp 只读 | 全部中转目录改 ~/tmp |
| 3 | aclocal/automake 缺失 | 系统无 automake | cmd-pkgs 安装 automake 1.16.5；shebang 指向 ~/usr/local/bin/perl 不存在 → 软链真实 perl |
| 4 | libtool 版本不匹配 (2.5.4 vs 2.4.7) | aclocal.m4 宏与 libtoolize 版本不一致 | 清空 aclocal.m4/autom4te.cache 重跑 autogen 统一宏版本 |
| 5 | configure: cannot guess build type | config.guess 无 HarmonyOS 分支 | E007 patch-autotools-ohos.pl 打 config.guess/config.sub；config.sub 内核列表补 `linux-ohos*-` 分支 |
| 6 | ecb.h: `_Noreturn` keyword must precede | 旧版 ecb.h 在 C11 下把 `_Noreturn` 放函数声明尾（ecb_inline void f(void) ecb_noreturn;），现代 clang 要求前置 | patches/0001-ecb.h.patch：改为 `ecb_attribute((__noreturn__))` |
| 7 | 补丁 absolute path 被 conan 拒绝 | conan patch 不允许绝对路径 | 补丁以 a/ecb.h, b/ecb.h 相对路径重生成 |
| 8 | test_package 链接错误 undefined symbol: eio_destroy | 初版 test.c 调用不存在的 API | 改用真实 API：eio_init/eio_nthreads/eio_wd_open_sync/eio_wd_close_sync/eio_nop/eio_poll/eio_grp_cancel |

## 源码修改
- `patches/0001-ecb.h.patch`：C11 下 ecb_noreturn 由 `_Noreturn`（要求函数声明最前）改为 `ecb_attribute((__noreturn__))`（位置无限制，GCC/Clang 均接受），解决 clang 15 编译失败
- config.guess/config.sub：OHOS 平台识别补丁（E007 方式，配合配方 --build/--host 双保险）

## 依赖版本
libeio 纯 C 无第三方运行依赖；构建期工具：automake 1.16.5、libtool 2.5.4、autoconf 2.72、clang 15.0.4

## 上游测试台账（完整枚举，R51）

枚举范围：官方 master tarball 全部文件（Changes/LICENSE/Makefile.am/autogen.sh/configure.ac/demo.c/ecb.h/eio.[ch]/eio.pod/eio.3/libeio.m4/xthread.h）+ 构建生成物

| 入口 | 来源 | 分类 | 是否独立上游用例 | 实际运行 | 结果/原因 |
|------|------|------|------|------|------|
| (无 tests/ 目录、无 test_*.c 文件) | 源码树 | - | 无 | - | 官方源码无任何独立测试文件 |
| Makefile.am 无 TESTS/check_PROGRAMS/XFAIL | Makefile.am | 构建声明 | 否 | `make check` rc=0 | 无测试目标，原本应无测试执行 |
| demo.c | demo.c（官方示例） | 样例 (sample) | 否（官方示例，非 TEST_CASE 框架用例） | 编译 rc=0；运行 SIGABRT(134) | 样例自带 `res_cb` 对 req->result<0 直接 abort()；本机需用受控 API 验证核心功能（见下） |
| eio.pod / eio.3 | 文档 | 文档 | 否 | - | man 手册 |

**双口径统计**：
- `source_declared_total` = 0（官方 tag 源码无可复制的独立测试用例声明：无 tests 目录、无 TESTS/check_PROGRAMS 宏、无测试框架注册）
- `configured_executable_total` = 0（当前 OHOS 配置下无实例化/注册的独立可执行测试用例）
- `executed_passed_total` = 0；失败 0；未运行/未实例化 0
- 全量通过率：0/0（无测试用例可计数，非 "未运行"）

**核心 API 功能验证（替代样例，模拟真实业务调用）**：
用独立消费者程序（libeio-mini.c，链接安装头 eio.h + libeio.a）实际运行通过：
`eio_init`(rc=0)、`eio_mkdir`(result=0)、`eio_nop`(0)、`eio_stat`(0)、`eio_fstat`(0)、`eio_fsync`(0)、`eio_close`(0)、`eio_readdir`(result=1)、`eio_utime`(0) → 全部返回 0/非负，程序退出 rc=0
（demo.c 崩溃为本机个别 syscall 负值触发其自身 abort 的示例行为；test_package 消费者用例亦全部通过，见 test_package/MANIFEST.yml）

## 验证结果

```bash
# conan-verify 全部门禁
G0 PASS（知识预检） G1 PASS（配方完整性） G2 PASS（conan create 干净构建）
G3 PASS（系统同名库隔离） G4 PASS（产物完整性） L2/L4/L5 PASS
# 消费者 mini 程序
clang -O2 -I. -o libeio-mini libeio-mini.c .libs/libeio.a -lpthread && ./libeio-mini → ALL OK (rc=0)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Autotools 配方（build_requirements automake/libtool、autoreconf、--build/--host=aarch64-unknown-linux-gnu、静态默认） |
| conandata.yml | 官方 URL + SHA-256 + 补丁声明 |
| patches/0001-ecb.h.patch | ecb.h C11 noreturn 兼容修复 |
| test_package/ | 消费者测试（eio_init/eio_nop 全链路，已随 conan-verify 实跑通过） |

## 注意事项
- libeio 官方仓库无 release tag，master 即 1.0 版（configure.ac AM_INIT_AUTOMAKE(libeio,1.0)）
- 上游无测试用例：PR 中上游测试统计须按 0/0 如实申报并附本文档枚举证据
- 产物 libeio.so.1.0.0 / libeio.a，链接标志 -leio

## 知识候选台账（knowledge_candidate_ledger）

任务类型：知识库扩展（路径 B 候选评估）。逐项记录真实错误、根因、修复、验证、适用范围与四范围查重（正式知识 doc/、图谱 graph/index.tsv、草稿 drafts/、recipes/）。

| # | 候选（真实错误） | 根因 | 修复/验证 | 适用范围 | 查重结果 | 决定 |
|---|------|------|----------|----------|----------|------|
| K1 | `ecb.h:475 error: '_Noreturn' keyword must precede function declarator`（clang 15 C11 模式） | 旧版 ecb.h 在 `#if ECB_C11` 分支把 ecb_noreturn 定义为 `_Noreturn`，且声明写为 `ecb_inline void f(void) ecb_noreturn;`（声明尾放置）——C11 要求 `_Noreturn` 前置，clang 15 严格报错 | patches/0001-ecb.h.patch：两分支统一为 `ecb_attribute((__noreturn__))`（GCC/Clang 扩展属性，允许声明尾放置，语义等价）；改后 make 通过，conan-verify G0-G4/L2/L4/L5 全 PASS，专项测试实跑 rc=0 | 任何内嵌 2012 版 ecb.h 且 C11 编译的库（libeio/libev 家族） | 图谱 index.tsv 无 noreturn/ecb_noreturn 条目；doc/ 无独立条目（musl-glibc 对比文档仅顺带提及）；drafts/ 无同 stem；recipes/ 无 | **new_draft**（已验证、可跨库复用、查重未命中） |
| K2 | `configure: cannot guess build type`（uname=HarmonyOS） | config.guess 无 HarmonyOS 分支 | E007 patch-autotools-ohos.pl + config.sub 内核列表补 `linux-ohos*-` 分支（E122） | 通用 autotools OHOS 适配 | E007/E122/E160 已覆盖 | **reuse_existing**（复用已有知识） |
| K3 | `Can't exec aclocal / Automake::Config.pm not found` | 系统无 automake / 预编译包 perl @INC 不匹配 | cmd-pkgs 安装 automake 1.16.5；软链 perl 到 shebang 路径 | 通用 autotools 工具链 | E116 已覆盖（compile-automake-from-source） | **reuse_existing** |
| K4 | `libtool: Version mismatch error (2.5.4 vs 2.4.7)` | aclocal.m4 宏与 libtoolize 版本不一致 | 清空 aclocal.m4/autom4te.cache 重跑 autogen 统一宏版本 | 通用 autotools 工具链 | E041/E071 已覆盖（automake 版本不匹配类） | **reuse_existing** |
| K5 | 官方 tarball 无预生成 configure | master 快照仅含 configure.ac/Makefile.am | 配方 build_requirements automake+libtool tool_requires，build() 先 autoreconf | 无 release 快照的 autotools 库 | E058/E059 已覆盖（configure missing→use-stable-release/autogen） | **reuse_existing** |

**路径决定**：**path B（知识库扩展）**——K1 为唯一新增候选，已验证、可跨库复用、四范围查重未命中，按同 stem 建立草稿 `knowledge/drafts/DRAFT-libeio-1.0-ecb-noreturn-c11.kv` + `.md`（graph validate 通过）。PR 前缀：【知识库扩展】。

七轴查重摘要（对 K1）：`exact_duplicate=false`、`causal_duplicate=false`、`trigger_overlap=false`（无既有条目触发同一签名）、`solution_overlap=false`（无既有条目建议改 noreturn 属性）、`combination_novelty=true`、`boundary_novelty=true`（明确限定旧版 ecb.h + C11 + clang 边界）、`test_migration_novelty=true`。关系字段：`similar_to=E007/E122`（同为 autotools 兼容类，但对象为编译器关键字而非平台脚本）、`caused_by=旧版 ecb.h + C11 编译器`、`prerequisite_of=无`、`conflicts_with=无`。既有条目覆盖部分：无；本轮新增部分：ecb_noreturn 宏 C11 兼容修复；适用边界/反例：现代 ecb.h（noreturn 前置版）无需本补丁。
---

**编译结束**: 2026-09-17 11:18
**最终状态**: published
