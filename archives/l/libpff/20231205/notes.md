# libpff 20231205 适配笔记

## 编译环境
- 构建系统: autotools（发布包自带生成的 configure/aclocal.m4/config.guess/config.sub/Makefile.in，配方不跑 bootstrap/synclibs）
- 编译日期: 2026-09-20
- 编译器: clang（OHOS NDK，/data/service/hnp/bin/clang，与 ci/conan/profiles/ohos-aarch64 一致）
- 状态: built
- 源码目录: 发布包自包含（17 个 libyal 本地组件 + 生成好的 Autotools 文件）

## 源码溯源

- 权威源：上游官方 GitHub release 资产 `libpff-alpha-20231205.tar.gz`
  （HTTP 200，2151000 字节，gzip 魔术 1f 8b，顶层目录 `libpff-20231205/`），
  sha256 `3e4932e3c68068b91b3024454ff095b941e326c4c15ea27ca727dc739004b880`。
- 互证源：Debian `libpff_20231205-1.dsc`（PGP 签名）Checksums-Sha256 声明
  `5389d05df51999e7e9dd02dcd238294763c929335b63b788b7c3576c0a063fc1 1187408 libpff_20231205.orig.tar.xz`，
  实测下载件哈希与字节数一致。Debian 将上游 gzip 重压缩为 xz，两归档哈希必然不同，
  故做**内容级**比对：两树解包后 1074 个文件逐文件 sha256 全树比对 FULL-TREE-IDENTICAL
  （抽样锚点：`configure` 两侧均为 `742bd217b6146e4ca6ba1e329ed6a2beacd50fce66045e669526e33f29beb990`）。
- 结论：GitHub 资产为权威源，Debian orig 为同内容发行版锚点。

## 语言预检（R47）处置记录

`lang-preflight` 对本包判 `mixed → env_unsupported`（exit 2），属工具误判，未采信：
- 工具证据自载：源文件 348 个，`.c` 340（97.7%）、`.sh` 9、`.py` 3、`.cpp` 3。
- `.py` 3 个 = 根级 `setup.py`（自述 "Script to build and install Python-bindings"）
  + `tests/pypff_test_file.py` + `tests/pypff_test_support.py`（两处在 tests/ 绑定测试目录）。
- 冲突源是根级 `pyproject.toml`（2023+ libyal 的 PEP517 布局，仅 `[build-system]` setuptools
  引导）+ 根级 `setup.py`——它们只打包 **pypff** Python 绑定（SWIG 生成，`pypff/*.c`），
  本包以 `--disable-python` 显式排除，不参与构建与交付。
- `.cpp` 3 个 = `ossfuzz/*_fuzzer.cc` 模糊测试夹具，不进构建。
- 按 R47 附录 D.4（绑定/辅助不算主体）与 c↔cpp 兼容族口径，主体语言为 C，与任务语言
  cpp 匹配。同族先例：libfsapfs（pyfsapfs）、libfsxfs 等已按同口径处置。设备侧语言判定
  不另行生成第二套流程，处置证据即本节。

## 编译步骤

配方 `conanfile.py` 内联完成（无补丁文件）：

1. `AutotoolsToolchain` 注入 `--disable-python --disable-java --disable-nls
   --enable-static-executables=no`；OHOS 下追加显式三元组
   `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`。
2. `build()`：umask 022；OHOS 下把 configure 内 `umask 077` 改写为 `022`（HMDFS 0700
   临时目录缺陷），以 `CONFIG_SHELL=/data/service/hnp/bin/bash` 解释 configure；
   `make -jN`（N=min(conf jobs,4)）；上游测试 `make -j1 check
   LOG_COMPILER=/data/service/hnp/bin/bash`，HOME 指向构建目录内一次性沙箱。
3. `package()`：`make install DESTDIR` 暂存 + COPYING/COPYING.LESSER 入 licenses。

原生探索（conan create 之前的同口径预演）关键读数：

- configure 特性摘要（逐字）：17 个捆绑组件全部 `local`；
  `DEFLATE compression support: zlib`；`Multi-threading support: pthread`；
  `Wide character type support: no`；`Python (pypff) support: no`；NLS `no`。
- zlib 为可选自动探测：`ac_cv_header_zlib_h=yes`、`ac_cv_lib_z_zlibVersion=yes`、
  `ac_cv_zlib=zlib`、`ac_cv_zlib_LIBADD=-lz`——命中 OHOS NDK sysroot 自带 zlib，
  设备与 CI 同一 SDK（同族先例 libfsapfs DRAFT-E590 同读数），不做 Conan require。
- 三元组现场取证：`./config.guess` 报 `aarch64-unknown-linux-gnu`（不识别 HarmonyOS
  主机名但回落 gnu）；`./config.sub aarch64-unknown-linux-ohos` **rc=1**（本版本
  config.sub 无 ohos 分支），`./config.sub aarch64-unknown-linux-gnu` rc=0——
  显式 gnu 三元组是唯一可选项（DRAFT-E587 同族差异口径的又一次实测）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 mixed→env_unsupported（exit 2） | 根级 pyproject.toml/setup.py（pypff 绑定打包 manifest）与 97.7% C 主体触发 §4.7 冲突 | 见「语言预检处置记录」；跳过该步留痕，不改工具、不采信假终态 |
| 2 | HMDFS 0700 临时目录 + 设备无 /bin/bash | HMDFS umask 语义 + OHOS 无 bash（E011/E087） | umask 022 + CONFIG_SHELL/LOG_COMPILER=/data/service/hnp/bin/bash |
| 3 | config.sub 拒绝 linux-ohos | 本版本（2023）config.sub 无 ohos 分支 | 显式 gnu 三元组（build==host，cross compiling=no） |
| 4 | tests/ 无 input 语料 | 上游 release archive 一贯不含 tests/input（E370 同族） | 依赖 input 的 runner 按上游自身规则 exit 77 SKIP；涉及程序按 NOT_RUN 申报 |

## 依赖版本

- 无外部 Conan 依赖（`conanfile.py` 无 `requires`；W0 清单 `w0-deps.txt` = none）。
- 17 个 libyal 组件全部为发布包内置 local 副本（版本随 20231205 发布包）。
- 系统 zlib（OHOS NDK sysroot）、pthread、dl——均为 SDK/平台内置。

## 验证结果

上游测试（原生探索轮读数，与 conan 采信轮同 SHA 同命令，最终数字以采信轮日志为准）：

```bash
make -j1 check LOG_COMPILER="/data/service/hnp/bin/bash"
# Testsuite summary（automake runner 面，另一计数单位）
# TOTAL: 5   PASS: 2   SKIP: 3   FAIL: 0
#   PASS: test_library.sh   PASS: test_tools.sh
#   SKIP: test_read_items.sh / test_pffinfo.sh / test_pffexport.sh（exit 77，无 tests/input）
# check_PROGRAMS 面（N 的统计单位）：注册 53 个 C 测试程序
#   执行 52 个全部 PASS（test_library.sh 驱动 49 = 47 个无参 + file/support 2 个带参；
#   test_tools.sh 驱动 3 = tools_info_handle/tools_output/tools_signal）
#   NOT_RUN 1：pff_test_read_items（上游 runner 因无 input 自跳过）
# 逐程序留证：tests/*.sh.log 逐程序 (PASS) 行（同源同命令原生探索轮副本：
#   $TASK_DIR/evidence-native/，test_library.sh.log 49 项、test_tools.sh.log 3 项）
# 程序化对账：注册表（tests/Makefile.am check_PROGRAMS 53 项）vs 驱动表并查，
#   差集仅 pff_test_read_items 一项；上游当前 HEAD 注册同为 53，无差额。
# 独立探针：./tests/pff_test_read_items（无参数）→ rc=1 "Missing filename."
#   ——与「需 PST 语料而发布包不含」一致，不构成可计入的执行
```

工具冒烟（暂存树）：

```bash
bin/pffinfo -V   # → "pffinfo 20231205"，rc=0
bin/pffexport -V # → "pffexport 20231205"，rc=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libpff.so.1.0.0（+.so/.so.1 链接） | 主库（LGPL-3.0-or-later） |
| include/libpff.h + include/libpff/*.h | 公开头文件 |
| bin/pffinfo、bin/pffexport | 命令行工具（commands.json 已登记） |
| lib/pkgconfig/libpff.pc、share/man/man1/*.1 | pkg-config 与手册页 |
| licenses/COPYING、licenses/COPYING.LESSER | 许可证文本 |

## 注意事项

- 上游 `tests/Makefile.am` 的 `check_SCRIPTS` 列表含 pypff/test_runner 等，但 automake
  实际注册执行的 TESTS 只有 5 个 shell runner（pypff*.py 未被运行，与其 conditional
  注册一致）——统计时以 automake 汇总行与 runner 日志实物为准，不按脚本名单推算。
- 本包 `pff_test_read_items` 需要 PST 语料；如后续任务要补齐该程序的真实执行，
  需自备语料并以独立探针口径记录，不得混入上游 runner 面计数。
- 工具链路径：CI profile 以 `tools.build:compiler_executables` 钉死
  `/data/service/hnp/bin/clang`；test_package 消费编译同源（R33）。
---

**编译结束**: 2026-09-20 11:07
**最终状态**: built
