# scws 1.2.3 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，libtool 2.4.2 时代脚本）
- 编译日期: 2026-09-26
- 编译器: clang 15（OHOS SDK，target aarch64-linux-ohos）
- 状态: built（本地 macOS 交叉验证；published 待 OHOS CI 通过后更新）

## 软件简介

SCWS（Simple Chinese Word Segmentation）是 hightman 开发的机械式中文分词引擎，
xunsearch 全文检索生态的分词组件。产物：libscws C 库 + scws / scws-gen-dict 两个
命令行工具。纯 C，无外部依赖（仅 libm）。

- 上游官网: http://www.xunsearch.com/scws/
- 上游仓库: https://github.com/hightman/scws
- 源码: https://www.xunsearch.com/scws/down/scws-1.2.3.tar.bz2
- SHA256: 60d50ac3dc42cff3c0b16cb1cfee47d8cb8c8baa142a58bc62854477b81f1af5

## 上游测试清点（先于适配执行）

**上游测试用例数 = 17**，唯一来源 `phpext/scws_test.php`（"SCWS auto test"）：

- 源码包无 tests/ / test/ 目录，4 个 Makefile.am 均无 TESTS、
  check_PROGRAMS、check-local，`make check` 为空操作；
- `phpext/scws_test.php` 的 `$TEST_DATA` 共 **17 条**用例，每条为
  「输入文本 + multi/ignore/duality 选项 + 期望分词结果」；
- 该脚本通过 php-scws 扩展运行（`$scws->set_dict(ini_get('scws.default.fpath') . '/dict.utf8.xdb')`），
  本仓库不引入 PHP 工具链，因此以 libscws **C API 逐条复刻**同样输入/选项/期望输出：
  `test_package/upstream_test.c`（T01-T17）；
- 其余目录（win32/ MSVC 工程、phpext/win32 的 zip/vcproj）不含测试。

**关键发现**：用例 01（马明练）、15/16（李姚明）依赖人名识别，必须
`--enable-namerule` 才能复现期望结果——本配方已在 generate() 中开启该选项。

统一计数口径：**上游按测试脚本原生用例数（17）计；适配后新增测试按
独立检查项计（9）**，贯穿 MANIFEST.yml / 本 notes / 测试日志 / PR 两张表格。

## 词典来源

上游词典 `dict.utf8.xdb`（官方发布件 `scws-dict-chs-utf8.tar.bz2`，
SHA256 `0f43956721561b1f5f0102b529dbe24a1aa15b9fb6c05446367db2717f462af3`）
不在源码包内，本配方作为第二 source 下载并安装到 `share/scws/dict.utf8.xdb`，
供上游用例复刻测试与下游用户使用。

## 编译步骤

```bash
conan create archives/s/scws/1.2.3 --user=ohpcd --channel=stable \
  -pr:h=~/.conan2/profiles/ohos-local -pr:b=default --build=missing
```

配方内部实际执行（CI worker 上为原生 OHOS 构建，本机为交叉构建）：

```bash
./configure --host=aarch64-unknown-linux-ohos \
            --enable-shared --disable-static --enable-namerule
            # 交叉时另加 --build 与探测缓存
make -j$(nproc)
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 OHOS worker（uname=HarmonyOS） | 2014 年版 config.guess 无 HarmonyOS 分支 | 0001 补丁新增 *:HarmonyOS:*:* 分支 → \<machine\>-unknown-linux-ohos（复用知识 E122/E268 同型方案） |
| 2 | config.sub 拒绝 aarch64-linux-ohos | 2014 年版不认识 linux-ohos OS 家族 | 0002 补丁在 maybe_os 与 OS 后缀表加入 linux-ohos* |
| 3 | CI worker 上 config.status 无法建临时目录 | HMDFS 给新目录强制 setgid 位，umask 077 → drwx--S--- 连 owner 不可写 | 0003 补丁 configure 临时目录 umask 077→022（与 libidl2 0.8.14 相同处理） |
| 4 | libtool 不生成 .so | host 三元组缺 vendor 位时 host_os=ohos，不匹配 libtool `linux*` 分支 | 显式 `--host=aarch64-unknown-linux-ohos`（libopendbx 1.4.6 已验证的教训，conanfile.py 内有注释） |
| 5 | 交叉构建时 AC_FUNC_MMAP 等运行时探测不可执行 | configure 交叉模式默认 "no"，会得到与 CI 原生构建不同的 config.h | 交叉构建时固定 ac_cv_func_mmap_fixed_mapped=yes 等 4 项缓存值（与 OHOS/musl 原生实测一致），保证两种构建路径行为相同 |
| 6 | 交叉构建时 libtool 只建符号链接、不生成 libscws.so.1.1.0 实体 | LT_PATH_LD 经编译器驱动探测到 macOS /usr/bin/ld，with_gnu_ld=no → archive_cmds 为空，链接步骤静默跳过 | 交叉分支固定 LD=ld.lld（报告 compatible with GNU linkers，生成 GNU 式 archive_cmds）、AR=llvm-ar、RANLIB=llvm-ranlib（均在 ohos-local profile 的 PATH 上）；CI 原生构建不覆盖，由 worker 环境自行探测 |
| 7 | make 阶段 cli 目录报 `No rule to make target .../libscws/libscws.la` | 上游 cli/Makefile.am 把 LDADD 写死为 $(top_srcdir)/libscws/libscws.la，Conan VPATH 构建时产物在 build 树而非源码树 | 0004 补丁 cli/Makefile.in 改用 $(top_builddir)（只改 .in 不碰 .am，避免触发旧 automake 重生成） |

## 源码修改

无 C 源码修改。3 个补丁全部位于构建系统平台识别层：
- patches/0001-config.guess-harmonyos.patch（+20 行）
- patches/0002-config.sub-linux-ohos.patch（2 行修改）
- patches/0003-configure-umask-022.patch（2 行修改）
- patches/0004-cli-makefile-vpath-libscws.patch（2 行修改）

## 依赖版本

无外部依赖（仅系统 libm）。

## 验证结果

### macOS 本机原生验证（test.c 逻辑预验证，2026-09-26）

```bash
# 本机 apple-clang 原生构建 scws 1.2.3 后运行 test_package 的 test.c
./test_scws . <prefix>/etc/rules.utf8.ini
# [PASS] T1 SCWS_VERSION == 1.2.3
# [PASS] T2 xdb_create/xdb_nput/xdb_optimize + reopen
# [PASS] T3 xdb dict segmentation 我爱北京天安门   (got: 我/爱/北京/天安门/)
# [PASS] T4 txt dict (MEM mode) segmentation       (got: 我/爱/北京/天安门/)
# [PASS] T5 packaged rules.utf8.ini + xdb segmentation
# exit=0
# CLI: scws-gen-dict 造词典 + scws -c utf8 分词 → "我 爱 北京 天安门" ✓
```

### OHOS 交叉编译（ohos-local profile）

见 conan-verify / finish 输出与 .ci-result.json。

### OHOS CI 运行（含鸿蒙特有测试 T6/T7）

待 CI 回填。

## 测试口径与数量

| 类别 | 数量 | 说明 |
|------|------|------|
| 上游测试用例 | 17 | phpext/scws_test.php $TEST_DATA，由 upstream_test.c 逐条复刻 |
| 适配后新增检查项 | 9 | test.c T1-T5（5）+ T6/T7 鸿蒙特有（2）+ test.sh C1-C2（2） |
| 合计 | 26 | 上游用例 17 + 新增检查项 9 |

鸿蒙特有测试与适配点对应关系：configure 的 AC_FUNC_MMAP / struct-flock
探测决定 libscws 的词典读（xdb.c mmap）与写锁（lock.c fcntl/flock）路径；
T6/T7 在 OHOS 上直接验证这两个系统调用的真实行为。

## 注意事项

- 词典文件（dict.utf8.xdb）上游单独分发、不在源码包内；test_package 用公共
  xdb API 现场构造小词典，覆盖写路径与 mmap 读路径。
- 文本词典非 MEM 模式会在 /tmp 落临时 xdb（xdict.c 硬编码 /tmp/scws-*.xdb），
  OHOS 上 /tmp 只读，消费方应使用 SCWS_XDICT_TXT|SCWS_XDICT_MEM
  （test.c T4 即此路径）。
---

**编译结束**: 2026-09-28 11:40
**最终状态**: built
