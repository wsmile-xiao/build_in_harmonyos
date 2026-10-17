# libfirm 1.22.0 适配笔记

## 编译环境
- 构建系统: makefile（libfirm 自带手写 Makefile，无 configure 脚本）
- 编译日期: 2026-09-07
- 编译器: clang/clang++（OHOS aarch64，`--print-target-triple` = aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

```bash
# 源码: 官方 tag libfirm-1.22.0 (2259fe4777fa51374c3f878a92b8467833e2b4f8)
# 官方 tarball: https://github.com/libfirm/libfirm/archive/refs/tags/libfirm-1.22.0.tar.gz
# sha256: 2e681db62610a41394f1aa3a62583acff8a67cea138354be6b3d2d8d390665c3
# 无 configure 脚本，直接用 make（-j1 规避 HMDFS jobserver fifo 限制）:
make -j1 CC=clang LINK=clang variant=optimize
# 安装验证（staging 隔离）:
make install DESTDIR=$TEST_PREFIX PREFIX=/usr/local INSTALL=/bin/install
# 上游测试:
make test CC=clang LINK=clang
# 配方验证:
ohc-run.py conan-verify libfirm 1.22.0   # G1-G4/L2/L4/L5 全通过
# finish（W2 结构 + R36 依赖 + W3 本地 CI 模拟）:
ohc-run.py finish libfirm 1.22.0 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 生成脚本报 `ModuleNotFoundError: No module named 'imp'` | Python 3.12 移除 imp 模块；gen_ir.py/irops.py 仍 `import imp` | `imp.load_source` → `importlib.util.spec_from_file_location`（0003/0004 补丁） |
| 2 | `ImportError: cannot import name 'Mapping' from 'collections'` | Python 3.10+ 将 Mapping 移入 collections.abc；vendored markupsafe/jinja2 2.8-dev 老旧 | `from collections.abc import Mapping`（try/except 兼容，0006/0007 补丁） |
| 3 | `re.compile(r'\w+(?u)')` 抛 re.error | Python 3.11+ 拒绝非起始位置内联正则标志 | `re.compile(r'\w+', re.UNICODE)`（0005 补丁） |
| 4 | `'.' is no longer in @INC` 导致 emitter 生成失败 | Perl 5.26 起 @INC 移除 `.`；generate_emitter.pl 用相对路径 `do` 架构 spec | 构建环境导出 `PERL_USE_UNSAFE_INC=1`（配方 generate() 注入） |
| 5 | `#error "Unsupported long double format"` (fltcalc.c) | aarch64 long double 为 IEEE quad（LDBL_MANT_DIG==113, 16 字节）；上游仅支持 64/53 | 增加 `LDBL_MANT_DIG==113` 分支，描述符 `{15, 112, 0}`（0002 补丁） |
| 6 | `firm_revision.h:1:1: error: expected identifier or '('` | tarball 无 .git 时 `git describe` 失败 → REVISION 空 + Makefile `\#define` shell 转义残留反斜杠 | Makefile 加 fallback 版本号并用 `printf '\x23define ...'` 输出（0001 补丁） |
| 7 | `make: jobserver mkfifo: Operation not permitted` | OHOS 文件系统不允许 make jobserver FIFO | `make -j1`（配方 build() 固定 -j1） |
| 8 | `/bin/sh: install: inaccessible or not found` | OHOS 环境无可用 `install` 命令（toybox 不含 install，/bin/install 不可执行） | 配方 generate() 用 busybox install 包装器加入 PATH |

## 源码修改

共 7 个补丁（patches/ 目录，均由 refresh-patch --auto 生成，无 __OHOS__ 平台宏）:

| 补丁 | 修改内容 |
|------|----------|
| 0001-Makefile.patch | firm_revision.h 生成：无 .git 时 fallback tag 哈希；去掉 `\#` 转义残留 |
| 0002-ir-tv-fltcalc.c.patch | 增加 LDBL_MANT_DIG==113（IEEE quad）描述符分支 |
| 0003-scripts-gen_ir.py.patch | imp → importlib.util（spec_from_file_location + exec_module） |
| 0004-scripts-irops.py.patch | 删除未使用的 `import imp` |
| 0005-scripts-jinja2-filters.py.patch | `(?u)` 内联标志 → `re.UNICODE` 参数 |
| 0006-scripts-jinja2-tests.py.patch | `collections.Mapping` → `collections.abc.Mapping` |
| 0007-scripts-markupsafe-__init__.py.patch | `collections.Mapping` → `collections.abc.Mapping` |

## 依赖版本

- 无外部依赖（libfirm 1.22.0 纯 C 库，requires 为空，W0 预检通过）
- 工具链: clang 15.0.4、make 4.4.1、Python 3.12.9、Perl 5.42.0、conan 2.29.1（OHOS 适配版）

## 验证结果

```bash
# 上游测试（make test，11 个 unittest 程序，142 个 assert）:
#   globalmap / nan_payload / rbitset / sc_val_from_bits / snprintf / strcalc /
#   tarval_calc / tarval_float / tarval_floatops / tarval_from_to / tarval_is_long
#   → 全部通过 (exit 0)；long double 分支由上游在 LDBL_MANT_DIG!=64/53 时跳过
# conan-verify: G1 配方完整性 / G0 预扫描 / G2 conan create / G3 系统同名库隔离 / G4 产物完整性 → PASS
# finish W3 本地 CI 模拟: L0 pass / L1 test_package 执行 / L4 patches clean / L5 lib 有内容 → 100% (1/1)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | make 驱动配方（无 configure，直接 make -j1 + 手工 package 头文件/静态库） |
| conandata.yml | 官方源 + sha256 + 7 补丁声明 |
| test_package/ | CMake 消费者测试（test.c 调用 ir_init/new_ir_prog/set_irp/new_id_from_str 真实 API） |
| patches/ | 7 个适配补丁（见上表） |
| knowledge/drafts/DRAFT-libfirm-1.22.0-*.{md,kv} | 4 对路径 B 知识草稿 |

## 注意事项

- 构建必须 -j1（jobserver fifo 不可用）且导出 PERL_USE_UNSAFE_INC=1
- install 命令在 OHOS 不可用，配方 generate() 通过 busybox 包装器提供
- aarch64 long double 是 IEEE quad（113 位），任何上游硬编码 64/53 分支的代码都可能需要 quad 分支
- `make install` 上游只装静态库 libfirm.a 与头文件（配方 package() 照此打包）
---

**编译结束**: 2026-09-07 01:10
**最终状态**: built

## 知识判定（oh-executor 本地快照流程）

- 官方快照: /storage/Users/currentUser/tianyi/knowledge_snapshots/libfirm-1.22.0-r01-bootstrap-and-adapt-pc2-39-20260906T150009Z
  repository=https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos.git ref=main
  HEAD=dfe3d3ac77fa7afa801d0a7223122e63f43802c3 sparse=knowledge（只读，HMDFS 忽略 chmod，git HEAD 钉定）
- 扫描范围: 正式 knowledge/graph/E*.kv（540 对 doc↔kv）、knowledge/drafts/*.{md,kv}（197 kv / 192 md）、根 DRAFT-* 配对
- 查重结论（逐字段 error_signature 比对）:
  - 等价命中（路径 A，不重复沉淀）:
    - install 命令缺失 → E098（error_signature 一致），另 E174 相近
    - Python 3.12 移除 imp（gen_ir.py/irops.py）→ E339（ModuleNotFoundError: No module named 'imp'）
    - make jobserver mkfifo（Operation not permitted）→ E074（jobserver.*fifo），草稿 DRAFT-eigen-3.4.1-make-jobserver-mkfifo-nonfatal 同签名
  - 无等价命中且可跨库复用（路径 B，创建草稿对）:
    - Perl >= 5.26 '.' 移出 @INC → DRAFT-libfirm-1.22.0-perl-unsafe-inc
    - Python 3.12 vendored jinja2/markupsafe（collections.Mapping、(?u) 正则）→ DRAFT-libfirm-1.22.0-python312-vendored-generators
    - aarch64 long double IEEE quad（LDBL_MANT_DIG==113）→ DRAFT-libfirm-1.22.0-aarch64-quad-long-double
    - Makefile tarball 无 .git 时 git describe 版本头损坏（\#define 转义）→ DRAFT-libfirm-1.22.0-makefile-version-header-tarball
- 快照无等价命中说明: E116/E155 为 perl 模块缺失类，不覆盖 '.' @INC 移除；E388/E257 为 Boost.Math 数值行为，不覆盖 fltcalc 编译期 #error
- knowledge_decision: new_draft（路径 B；标题前缀【知识库扩展】）
- 草稿对字段一致性/成对/哈希: 4 对 md↔kv 均配对且 id/error_signature/root_cause/rec_approach/doc_file/draft 齐备；SHA-256 见最终报告
