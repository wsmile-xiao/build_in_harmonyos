# libxdg 1.2.3 适配笔记

## 编译环境
- 构建系统: autotools（tar 不含 configure/Makefile.in，需 autoreconf bootstrap）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang），目标 aarch64-linux-ohos
- 状态: built（conan create 通过 ohos-aarch64 profile）

## 上游身份
- 仓库: https://github.com/devnev/libxdg-basedir （默认分支 master）
- release tag: `libxdg-basedir-1.2.3`（**无 `v` 前缀**；`archive/refs/tags/v1.2.3.tar.gz` 为 HTTP 404）
- tarball SHA-256: `ff30c60161f7043df4dcc6e7cdea8e064e382aa06c73dcc3d1885c7d2c77451d`
- 解出目录 `libxdg-basedir-libxdg-basedir-1.2.3`，配方 `strip_root=True` 拉平
- 许可: MIT（COPYING 随 make install 之外单独 copy 到 licenses/）

## 编译步骤
1. `apply_conandata_patches`：打 patches/0001（VPATH 期望路径修复，见下）。
2. `autoreconf -fi`（cwd=source_folder）：tarball 只有 configure.ac/`m4/`，生成 configure、
   Makefile.in、config.guess、config.sub、ltmain.sh。
3. `_patch_ohos_triplet()`（E007）：对**刚生成**的 config.guess/config.sub 就地改 5 处，
   并 `chmod 0755`（重写文件若丢执行位，configure 会以
   `cannot run .../config.sub` 失败）。
4. `_drop_umask_077()`（E114/E011）：把生成 configure 里所有 `umask 077` 换成 `umask 022`。
5. `autotools.configure()` → `autotools.make(-j1)` → `autotools.make(target="check", -j1)`。
6. `_emit_upstream_test_result()`：从 build 树里的 `test-suite.log` 解析
   TOTAL/PASS/FAIL/SKIP/XFAIL/XPASS/ERROR，发出 `HMBS_UPSTREAM_TEST_RESULT=` 标记。
7. `autotools.install()`；删除 `lib/*.la`（libtool 包装脚本内嵌绝对构建路径）；
   copy COPYING。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | config.guess 不识别 HarmonyOS（`uname -s` 字面量 "HarmonyOS"），也不认 `__OHOS__` 的 libc | E007：build() 内联等价 patch-autotools-ohos.pl —— config.guess 加 `#elif defined(__OHOS__) / LIBC=ohos` 分支与 `*:HarmonyOS:*:*` case；config.sub 加 `ohos-linux)` 基本机 + `ohos*` OS 项 + `linux-ohos*` 内核-OS 白名单项 |
| 2 | `configure: error: cannot run /bin/bash .../config.sub` | 上一步用 Python 重写 config.guess/config.sub 后，Windows 侧 `open(..., "w")` 把 `\n` 转成 `\r\n`，且执行位丢失 | 两处修复：所有 `open()` 加 `newline=""` 做字节透明读写；函数末尾对两个 helper `os.chmod(..., 0o755)` |
| 3 | `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied` | E114：HMDFS 强制目录 setgid，configure 内 `umask 077 && mktemp -d` 生成 drwx--S--- 目录，连属主都不可写 | E114：build() 运行时 `_drop_umask_077()` 把生成 configure 的 `umask 077` 全替换为 `umask 022`（a52dec/adcli/univalue 同款） |
| 4 | `make: jobserver mkfifo: Operation not permitted` | E074：鸿蒙 SELinux 拒绝 jobserver FIFO | configure/make/make check 全部 `-j1` |
| 4b | autoreconf/autom4te 写入 `/tmp` 失败 | OHOS 上 `/tmp` 只读；配置里 `mktemp -d ./confXXXXXX` 虽是 cwd 相对，autoreconf 的 autom4te 不是 | `_prepare_build_env()`（generate() 与 build() 各调用一次）把 `TMPDIR` 指向 `build_folder/tmp`（`makedirs` + `chmod 0755`），accel-config/4.1.9 同款 |
| 5 | `make check` 稳定 2/31 失败（querycf.2、querydf.2） | 上游 `tests/querycf.2`/`querydf.2` 用 `wd="$(pwd)"` 拼期望路径 `"$wd/${top_srcdir}/tests/$basename"`，只有当 `${top_srcdir}` 是**相对**路径时才等于真实位置；Conan 一律以绝对路径调用 configure（VPATH out-of-tree），拼出 `/<abs>/<abs>/tests/...` | patches/0001：改用 `td="$(cd "${top_srcdir}/tests" && pwd -P)"` 解析真实目录，`XDG_*_DIRS="$td"`、`expected="$td/$basename"`。已做对照实验：相对路径 configure → 31/31；绝对路径 configure → 29/31；打补丁后绝对路径 → 31/31 |

## 源码修改

patches/0001-tests-query-harness-vpath-absolute-top-srcdir.patch —— 只动 `tests/querycf.2`
与 `tests/querydf.2` 两个 shell 用例，不触碰被安装的库代码（src/、include/ 零改动）。
属于通用 out-of-tree 构建修复，与 HarmonyOS 无关，可直接向上游提交（P005）。

生成文件（configure / config.guess / config.sub / Makefile.in / ltmain.sh）的修复全部
放在 build() 运行时完成，不进 patches/，conandata 只声明上面这一个补丁。

## 依赖版本
- 无第三方运行时依赖（standalone 库）。
- tool_requires: automake/1.18、libtool/2.5.4（autoreconf bootstrap）。

## 验证结果

本地对照实验（WSL x86-64 glibc，绝对路径 configure + `make -j1 check`）：

```bash
# 不打 0001：29/31（querycf.2、querydf.2 FAIL）
# 打 0001  ：31/31
# TOTAL: 31  PASS: 31  FAIL: 0  ERROR: 0  SKIP: 0
# test-suite.log -> <build>/tests/test-suite.log
```

消费者测试（gcc -std=gnu99 -Wall -Wextra，无告警；连续 3 次运行结果一致）：

```
ALL PASS: libxdg 1.2.3 consumer checks (6 groups, 51 checks, TMPDIR=...)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 自包含 autotools 配方（autoreconf bootstrap + E007 三元组 + E114 umask + E074 -j1 + make check + HMBS 标记） |
| conandata.yml | 官方 URL + SHA-256 + patches 列表 |
| patches/0001-…-vpath-absolute-top-srcdir.patch | VPATH 期望路径修复（通用，可上游） |
| test_package/ | 消费者测试 test_libxdg.c（6 组 51 断言，含鸿蒙 ABI/HMDFS/多线程专项）+ CMakeLists + conanfile + MANIFEST.yml |
| manifest.yaml / notes.md | 版本元数据与适配笔记 |
| knowledge/drafts/DRAFT-libxdg-1.2.3-*.{md,kv} | 知识库扩展草稿 |

## 注意事项

- 任务路径：【知识库扩展】。新增知识条目见
  `knowledge/drafts/DRAFT-libxdg-1.2.3-vpath-absolute-top-srcdir-test-paths.{md,kv}`，
  主题为「out-of-tree(VPATH) 构建下上游 shell 用例用 `pwd` 拼绝对 `${top_srcdir}`
  期望路径必失败」；与 E434（automake copystamp：in-tree 构建反而失败、必须
  VPATH 构建）方向相反，互为补充。
- `make check` 的 TESTS 由 automake parallel-tests 驱动；上游默认分支 master 的
  `tests/` 与 tag `libxdg-basedir-1.2.3` 逐字节相同（`git diff` 无输出），
  rule4 的 N=31 对 master 口径同样成立，无少报。
- 静态库链接用 `-lxdg-basedir`（`cpp_info.libs = ["xdg-basedir"]`），
  安装布局：`include/basedir.h`、`include/basedir_fs.h`、`lib/libxdg-basedir.a`。
- test_package 运行期由 conanfile.py 注入 `TMPDIR`（OHOS 上 `/tmp` 只读）。

---

**编译结束**: 2026-09-19
**最终状态**: built
