# libstorj 1.0.3 — OHOS PC 适配记录

- 上游: https://github.com/storj-archived/libstorj （原 Storj/libstorj，已归档；tag 归档即官方源）
- 版本: 1.0.3（上游最后发布线，Debian/Fedora 同版在册）
- 任务: feat/libstorj-1.0.3（积分赛，新包 --allow-unpublished：upstream/main 无 archives/l/libstorj）
- 配方: archives/l/libstorj/1.0.3/conanfile.py（autotools 模板 + 自举/依赖注入适配）

## 源码溯源（R39 双源互证）

- 官方下载入口 = GitHub tag 归档（v1.0.3 release **无**源码资产，
  releases/expanded_assets 页仅列 archive/refs/tags 两个入口，实测 2026-09-21）：
  `https://github.com/storj-archived/libstorj/archive/refs/tags/v1.0.3.tar.gz`
  sha256 `0f68f6a8374b93c240ae3a87c2f08feb34f812685858935bf079c1d0501ad032`（170838 字节，
  gzip 魔术 1f 8b，tar 顶层目录 libstorj-1.0.3/）。
- Debian pool `libstorj_1.0.3.orig.tar.gz`
  （http://deb.debian.org/debian/pool/main/libs/libstorj/）与上者**字节级同源**：
  同 170838 字节、同 sha256 —— 双源最强形态，无重压缩差异。

## 语言预检（R47/W0b）

- lang-preflight 判定 detected=c，与主体一致（src/*.c 18 文件、test/*.c 5 文件，
  均为 C89/C99；无绑定、无 vendored 异构构建入口）。`status=partial` 仅是 R46
  生命周期草稿（任务进行中非终态），无 §4.7 冲突。

## 依赖（W0，ohpcd 远端实测 2026-09-21）

| configure.ac 要求 | 配方 require | 远端现状 |
|---|---|---|
| libcurl >= 7.35.0 | libcurl/8.5.0 | 在册（制品仅共享库，无 libcurl.a） |
| nettle >= 3.1 | nettle/3.10.2.1 | 在册（3.9.1/3.10.2.1/4.0，取 3.10 稳定线） |
| json-c >= 0.11 | json-c/0.18 | 在册（0.17/0.18） |
| libuv >= 1.8.0 | libuv/1.52.1.1 | 在册（1.52.1/1.52.1.1，静态+共享双形态） |
| libmicrohttpd >= 0.9 | libmicrohttpd/1.0.1 | 在册（仅测试用：mock bridge/farmer） |

- 间接：nettle → gmp（nettle.pc `Requires: gmp`，Conan 图自动带入）。
- 工具链（build profile）：automake/1.18 + libtool/2.5.4（CI worker 缺
  automake/aclocal/libtoolize，E178）；autoconf 用 HNP 自带套件
  （/data/service/hnp/bin），**故意不** tool_requires conan autoconf/2.72
  （PERL5LIB 毒丸，device-facts §一.23）。

## 配方适配点（配方逻辑全部在 conanfile.py；源码侧改动见 patches/ 0001–0005，其中 0001 只改构建文件，0002/0004/0005 触及生产源码，0003 只改测试构建文件）

1. **tag 归档无 configure**：build() 先 `autoreconf --install`（tool_requires
   提供 automake/libtoolize），再对生成的 configure 做 E114 umask sed
   （HMDFS 上 `umask 077` 临时目录必现 `can't create ./confXXXX/subs1.awk:
   Permission denied`，本任务 2026-09-21 探针独立复现）。
2. **显式三元组**：LT_INIT 隐式引入 AC_CANONICAL_HOST（libtoolize 安装
   config.guess/sub），而 conan 对 os=OHOS 不产三元组参数 ⇒ configure 运行
   config.guess 猜 build 类型：2024-07 版不认 `uname -s = HarmonyOS` 且其
   TMPDIR 编译探针在 HMDFS 上被拒（`dummy.c: Permission denied`）
   ⇒ `cannot guess build type; you must specify one`（探索轮 1 实测）。
   配方显式传 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
   （config.sub 2024 版接受 *-linux-ohos），configure 记录
   `checking build/host system type... aarch64-unknown-linux-ohos`、
   `cross compiling... no`。
3. **依赖共享库运行路径**：AutotoolsDeps 只注入 CPPFLAGS/LDFLAGS/LIBS，
   不注入 LD_LIBRARY_PATH ⇒ configure 的 conftest（全量 -lcurl/-luv/-ljson-c
   链接）运行时 `Error loading shared library libuv.so.1` rc=127 ⇒
   `cannot run C compiled programs`（探索轮 2 实测）。配方把依赖 libdirs
   追加进 buildenv LD_LIBRARY_PATH，configure 与 `make check` 一并受益。
4. **libuv.pc 别名**：远端 libuv 包 cpp_info 的 pkg_config_name 是
   `libuv-static`，PkgConfigDeps 只产 `libuv-static.pc`，而 configure 要找
   模块名 `libuv` ⇒ `libuv1 1.8.0 or greater was not found`（探索轮 3 实测）。
   generate() 在生成目录写 `libuv.pc` 别名（Name 行改写）。
5. **0001 补丁（去 -static）**：上游 `storj_LDFLAGS = -Wall -static`、
   `tests_LDFLAGS = -Wall -g -static -lmicrohttpd` 整体静态链接，而 ohpcd
   libcurl 制品**无 libcurl.a**（仅 libuv/json-c 双形态、nettle/microhttpd
   纯静态）⇒ `-lcurl` 在静态模式必失败。工具链本身支持静态（clang -static
   探针 → ELF EXEC 且运行 rc=0，2026-09-21 取证），缺口只是依赖归档，故去
   两处 `-static`；库本体仍 R26 静态优先（--enable-static --disable-shared）。

## 上游测试（make check，TESTS = tests tests_rs）

- `tests`：API/上传/下载/BIP39/加密/工具组，驱动本地 libmicrohttpd mock
  bridge（:8091）+ mock farmer（:8092），纯回环无外网；`PASS/FAIL` 逐条 +
  末尾 `PASSED: N ... TOTAL: M`。
- `tests_rs`：Reed-Solomon FEC 单测（assert 驱动，9 个测试函数 + 2 个基准），
  成功标志 `reach here means test all ok`。
- 测试夹具生成：test/Makefile.am 的 `%.json.h` 规则用
  `hexdump -v -e '8/1 "0x%02x, "'` 把 mockbridge.json 转字面量数组 —— HNP
  hexdump（/data/service/hnp/bin/hexdump）实测支持该格式串（含 `0x  ,` 填充
  形态，Makefile 的 sed `s/0x  ,//g` 正常剥除）；configure 的
  `AC_PATH_PROG(HEXDUMP)` 在设备/CI worker PATH 内可命中。
- `tests.c` main() 要求 `$TMPDIR` 非空否则 exit(1)：配方固定以可写的
  build-local 目录驱动 `make check`。
- 计数口径（§3.5，上游与适配后同单位）：见 reports/test-report.md 与
  manifest tests 段（以采信轮设备日志实数为准，不在此预填）。
- test_package 消费者断言 **8 条**（独立计数，不并入上游分母）：时间戳、
  mnemonic 校验正/反、mnemonic 生成回环、加密授权写读回环、错口令拒绝、
  strerror、CLI --help 冒烟。

## 设备边界留证（本任务命中）

- init-build 嵌套源码误提升（depends/ 被当源码根，真实树被弃）：绕行 +
  登记见 `feedback/pending/2026-09-21-libstorj-1.0.3.md` F1。
- 其余 umask/三元组/LD_LIBRARY_PATH/pc 别名证据：探索轮 1–4 日志
  （$WORKSPACE_ROOT/tmp/libstorj-create-explore{,2,3,4}.log）+ 采信轮留档
  reports/。

## 知识沉淀（路径 B）

- DRAFT-E634-libstorj-library-temp-path-tmp-readonly-storj-temp：库自选临时目录
  （TMPDIR 死代码分支 + STORJ_TEMP 覆盖 + /tmp 只读兜底陷阱）与 fallocate EACCES
  的判读序；manifest.knowledge_gained 行尾 `# knowledge_ref:` 引用。
- DRAFT-E635-ohos-static-exec-supported-shared-only-deps-judgment-order：
  OHOS 工具链支持 -static 可执行（探针取证）与「依赖制品只发共享库」缺口的
  三步判读序（先探针工具链、再查依赖 .a、最后才动补丁）。
- 既有条目引用：E114（umask）、E007（三元组）、E467（AutotoolsDeps LIBS 与
  conftest 运行）、E384（pkg_config_name 与上游模块名错位）。
---

**编译结束**: 2026-09-21 12:07
**最终状态**: built
