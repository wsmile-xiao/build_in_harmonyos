# libgsf 1.14.58.2 适配笔记（任务卡 4316·火种 5；本仓 4 段本地修订版）

## ⚠️ 版本性质问题表（强制披露 ①④：四项披露之 notes 落点）

| # | 事实 | 证据 |
|---|------|------|
| 1 | **上游无 `LIBGSF_1_14_58_2` tag**（且历史上从无任何 4 段 tag） | `git ls-remote --tags https://gitlab.gnome.org/GNOME/libgsf.git` 全量 84 个 tag：`1_14_58 → 1_14_59` 直跳；精确 grep `1_14_58_1\|1_14_58_2` 零命中；全 refs（heads+tags）grep `58_1/58_2/58.1/58.2` 零命中；GitHub 镜像、GitLab tags/releases API 同结论 |
| 2 | **官方发行渠道 404，无任何 1.14.58.2 可构建发行物** | `download.gnome.org/sources/libgsf/1.14/libgsf-1.14.58.2.tar.xz` HEAD=404（58.1 同 404、58=200）；GitLab archive 两种 tag 命名 404；目录清单与 NJU 镜像只有 …58/…59；conan-center-index `recipes/libgsf/config.yml` 只有 1.14.58 |
| 3 | **本版本 = 本仓「4 段 = 本地修订版本」既有约定，非上游新版本** | 同包先例 `1.14.58.1`：上游同样无独立 tag、源同为 LIBGSF_1_14_58 归档，已合入 main `6568938da` 且 ohpcd published；`glib/2.84.0.1` notes 明文「原位修订：…**上游源码仍为 2.84.0 tarball**」；本仓 `archives/` 现存 **247 个 4 段版本目录** |
| 4 | **源字节与 1.14.58.1 逐字节同源（sha256 同源检测命中）** | 实测 GitLab `LIBGSF_1_14_58` 归档 sha256 `5254e2a571f6ae29f188f51f5c37b66e54a6cf660ec32c9da72c43125db2eca7` = 1.14.58.1 conandata 记录值（候选 B：官方 `libgsf-1.14.58.tar.xz` 实测 `06e07ea12b7a…` = 1.14.58 conandata 值） |
| 5 | **零源码 delta：构建输入面 diff 仅为版本号位移** | `diff -r 1.14.58.1 1.14.58.2` = conanfile.py 2 行（docstring+version）、manifest.yaml 版本/日期/知识引用、test_package/MANIFEST.yml package 行；`conandata.yml`、`patches/`（6 个）、`test_package/conanfile.py+CMakeLists+test.c` **零改动**。**原位修订=版本号位移、零源码 delta，不得包装成上游新版本** |
| 6 | 证据档（编排方裁决要求全部保留） | `$HOME/tmp/libgsf-1.14.58.2/w0-evidence/`：`run-w0-gates.sh` + `w0-gates-2026-09-23.log`（150 行逐字读数）+ 候选源实体 + 上游索引页 + 上游测试清点文件 |

> W0-1 曾按生死关命中止损上报，编排方裁决（2026-09-23）：**采信止损上报 + 按「本仓 4 段=本地修订」约定授权恢复执行**；并强制上述披露（notes 本表 / feedback 同款条目 / PR 正文版本说明段 / 零源码 delta 如实写）。**上游已发 1.14.59（2026-09-20，tag+官方 tar.xz 在档）——另案升级任务，本任务不改版本号**（任务卡 4316 钉 1.14.58.2，分支名门禁 包目录名-版本==分支，擅改=越权）。

## W0 四关（裁决后补全）

| 关 | 结论 | 读数 |
|----|------|------|
| W0-1 版本可得性 | 命中 → **裁决授权**（按 4 段本地修订继续） | 见上问题表 1–4；证据 `w0-gates-2026-09-23.log` |
| W0-2 硬依赖**真实组合验证** | ✅ rc=0 | `conan install --build=missing -pr:h=<绝对路径> -pr:b=<绝对路径>`（conanfile.txt：glib/2.84.0.1+libxml2/2.15.3.1+zlib/1.3.1.1+tool_requires automake/1.18+libtool/2.5.4）→ `Install finished successfully`；7 个 ref 全部 `Cache`/`Download(ohpcd)`，**无 conancenter 源码构建**；libffi/3.4.4#ca8b0eb、pcre2/10.45#5ecd2f9 随 glib 解析落 ohpcd（与 58.1 R48 pin 值一致）。日志 `$TASK_DIR/w0-combo/w0-2-install.log`，rc 存 `$TASK_DIR/w0-combo/w0-2.rc` |
| W0-3 平台判据 | ✅ 零命中（非止损项） | 对候选 A 源码树 grep `altivec.h\|mmx\|3dnow\|immintrin\|printf.h\|register_printf_`（*.c/*.h/*.S）→ rc=1 |
| W0-4 SKILL W0 官方两法 | ✅ 双法全过 | 方法一 `bash ci/scripts/preflight_check.sh libgsf/1.14.58.2` rc=0（gettext/0.22.5、glib/2.84.0、libxml2/2.15.3、zlib/1.3.1 已发布；R37 版本号未占用）；方法二 `conan download --only-recipe -r=ohpcd` 5/5 rc=0（含两个 tool_requires，R35 不用 list 代替） |

W0b：历史 notes 必读——本任务**精读 1.14.58.1 全文**（最近版、abiword 协作者归档）+ 1.14.58/1.14.53 标题速览；CI 能力矩阵：autotools+C ✅，需 `tool_requires automake/1.18`+`libtool/2.5.4`（配方已带、ohpcd 已发布），无 Rust/OCaml。

## 配方要点（逐文件复用 1.14.58.1，delta 58.1→58.2）

- 源：GitLab release 归档 `LIBGSF_1_14_58`（无 configure → build() 内 `autoreconf --force --install` 引导），sha256 同 58.1。
- 补丁 6 个全复用（strip: 1）：0001-config.guess / 0002-config.sub / 0003-gtk-doc.make / 0004-gtkdocize / 0005-m4-ohos-gtkdoc-stub.m4 / 0006-configure.ac-gtkdoc。
- configure triplet：`--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`（交叉探测不运行 conftest）；`--disable-gtk-doc --disable-nls`；`make -j1`（E074）。
- HMDFS 修复随配方：`ac_tmp=./fixed_tmp`（E129/E167 族）、`AUTOM4TE/SED/AUTOCONF/AUTOHEADER` 环境覆盖（E089）、`AUTOPOINT/gettext_datadir` 显式指向、LDFLAGS 用 conan 依赖 libdirs 前置 + `-lintl`（E107/E142）。
- 依赖：glib/2.84.0.1、libxml2/2.15.3.1、zlib/1.3.1.1（W0-2 实测 ohpcd 组合可解）。

## 测试口径（清点，N 下界=上游 HEAD 注册数）

- 被审源（LIBGSF_1_14_58）`tests/`：**perl 测试磁盘 15 个**（`TESTS` 注册 14 + `t8040-valgrind-tar.pl` 未注册进 automake TESTS，按 Septest 审查口径一并补报）+ **`check_PROGRAMS` C 程序 34 个** → 候选数法最大值 **N=49**（15+34，两口径不混用、差额已归因）。
- 上游当前 HEAD（master）`tests/Makefile.am` 注册数 = TESTS 14 + check_PROGRAMS 34 = **48**，与被审版本逐项比对**零差额**（清点文件 `$TASK_DIR/w0-evidence/upstream-TESTS.txt`、`master-checkprogs.txt`、`v58-checkprogs.txt`）。
- 执行计划：①perl 15 个（需 XML::Parser；设备当前缺失——`perl -MXML::Parser` 实测 `Can't locate XML/Parser.pm`，尝试装入 `$TASK_DIR/test-home` 沙箱前缀，装不上则如实 NOT_RUN 并给证据）②C check_PROGRAMS 自包含子集从采信轮构建树实跑（test-ole/test-compress/test-csv/test-xml/test-msole-dup/test-iconv，1.14.58 同源先例口径）③`test_package` 消费者 1 个 = **鸿蒙特有测试行 ≥1**（rule12）。
- 四分项 `TOTAL = PASS + FAIL + SKIP + NOT_RUN`，实测数字全部来自最终设备日志 → `reports/test-report.md` + PR 正文；不估算、不沿用 58.1 的旧数字。

## 状态

- 配方落盘 → 采信轮（`conan_verify_round.sh` rc 硬判）→ 上游测试实跑 → `finish built` → W4 独立审计 → 提审。实测读数见 `reports/test-report.md`（ignored，不进 PR）与 PR 正文。

## 附：1.14.58.1 归档笔记（历史参考，非本任务执行记录）

<details><summary>展开 1.14.58.1 notes（abiword-plugin-sdw 编译协作者验证归档）</summary>

### 编译环境
- 构建系统: autotools（GitLab release 归档无 configure → build() 内 autoreconf 引导）
- 编译日期: 2026-08-14；编译器: clang 15.0.4（aarch64-linux-ohos，OHOS PC）
- 状态: built（conan-verify 8/8 通过；ohpcd 未发布 libgsf，不强行上传）——**后续已发布**（`conan list libgsf/1.14.58.1 -r=ohpcd` 实测在档）

### 遇到的问题与解决方案（58.1 归档）
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitLab 归档无 configure | 非 release tarball | build() 内 `autoreconf --force --install` 引导 |
| 2 | configure 不识别 aarch64-*-ohos (E007) | config.guess/sub 无 OHOS 分支 | 0001/0002 补丁 |
| 3 | autoreconf 强制调用 gtkdocize | configure.ac 含 GTK_DOC_CHECK | 0003-0006 stub 补丁 |
| 4 | make 并行 jobserver FIFO 禁止 (E074) | HMDFS + SELinux | `make -j1` |
| 5 | 链接选中旧静态 glib (E107/E142) | 全局 LDFLAGS=-L/usr/local/lib | LDFLAGS 用 conan 依赖 libdirs 前置 + -lintl |
| 6 | config.status 无法写临时目录 (E129/E167) | HMDFS mktemp setgid 权限 | ac_tmp 固定到预创建 fixed_tmp |
| 7 | 上游 make check perl 测试 | OHOS 预装 perl 缺 XML::Parser | 装 XML::Parser 2.59 + Expat 2.7.3 后实跑（58.1 归档：11/14 PASS） |

### 58.1 归档验证结论（历史，不作为本任务读数）
- conan create 全流程成功；conan-verify G0-G4+L2/L4/L5 八道门禁 PASS；recipe 343a41cf + armv8 包 b7b65de8
- perl 测试 14 项实跑：11 PASS / 1 FAIL（t2000-iconv，平台 glib iconv 语义差异，非库缺陷）/ 2 SKIP（valgrind 缺失）

</details>
