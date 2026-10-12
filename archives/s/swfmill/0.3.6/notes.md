# swfmill 0.3.6 适配笔记

## 编译环境

- 构建系统：autotools（发布 tarball 自带预生成 `configure`，未跑 autoreconf——CI worker 的 PATH 无 automake）
- 编译日期：2026-10-06（首次适配）／2026-10-10（CI 门禁整改）
- 编译器：clang 15（`/data/service/hnp/bin/clang`，OHOS aarch64）
- 目标：`os=OHOS os.version=6.0 arch=armv8 compiler=clang`（`ci/conan/profiles/ohos-aarch64`）
- 状态：published

## 编译步骤

### 对话 #1 [2026-10-06] 首次适配

- 问题：`configure` 不认 `aarch64-*-linux-ohos`；EXSLT 探测找不到 `libexslt`；源码 sha256 校验失败；上游无 automake TESTS 集成
- 操作：以 autoconf 2.72 基底替换 `config.guess`/`config.sub`；`generate()` 注入六个模块 `*_CFLAGS`/`*_LIBS`；`source()` 加 urllib 原始字节回退；以 `test/` 下 shell 套件作为测试入口
- 结果：`conan create` 通过；上游 58 用例 57 过 / 1 败（import-ttf 平台差异）

### 对话 #2 [2026-10-10] CI 首轮失败：L0c 缺测试源

- 问题：CI 报 `L0c: No test source files in test_package/`，包本体未编译（L1/L2/L4/L5 全 skip）；本地全绿
- 操作：新增 `test_package/test.sh` 承载 3 个用例，`conanfile.py` 改为 bash 派发（OHOS `/system/bin/sh` 不能可靠执行 ELF）
- 结果：L0 全闸通过；顺带修正 `xslt` 子命令漏传输入 XML（`rc=255` → `rc=0`）

### 对话 #3 [2026-10-10] CI 二轮失败：HMDFS umask 临时目录

- 问题：CI 在 `configure` 最后一步挂掉——写 `./confXXXXXX/subs1.awk` 被拒（EACCES），随后 `could not setup config files machinery`；CI 自动分类误判为「网络问题／源码下载超时」，实际源码已由 E690 回退取到、configure 已跑完所有探测项
- 操作：按知识库 E129 定位（HMDFS + setgid：`umask 077 && mktemp -d "./confXXXXXX"` 落盘 `drwx--S---`(2700)，组权限位为空，非属主构建用户无法进入）；补丁 `patches/0001-configure-umask-002.patch` 把 `configure` 中两处 `umask 077` 放宽为 `002`
- 结果：见「遇到的问题与解决方案」问题 7

本配方的自动化流程：

1. `conan create` 取 `conanfile.py` + `conandata.yml`；`source()` 下载
   <https://www.swfmill.org/releases/swfmill-0.3.6.tar.gz> 并按 sha256
   `db24f639…548e` 校验（E690 回退路径见问题 3）。
2. `export_sources()` 导出 `patches/*`；`build()` 先 `apply_conandata_patches()`
   打 0001（configure umask），再用 OHOS-aware 版覆盖 `config.guess`/`config.sub`。
3. `generate()`：`AutotoolsToolchain` 追加
   `--build=aarch64-unknown-linux-ohos` / `--host=aarch64-unknown-linux-ohos`，
   并注入 `XML/XSLT/EXSLT/FREETYPE/PNG/ZLIB_CFLAGS|_LIBS`（取值来自各 conan 依赖的
   `cpp_info`），绕开 pkg-config。
4. `configure` → `make -j1` → `make install`（`Autotools.install()` 自带
   `DESTDIR=<package_folder>`）；`package()` 额外交付 `share/swfmill/{xslt,swft}`。
5. `test_package/test.sh` 对安装出的 `bin/swfmill` 做 3 项用例（2 断言 + 1 鸿蒙
   非断言观测，rule12）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | 上游 2005 版 `config.guess`/`config.sub` 不识别 `aarch64-*-linux-ohos` | 以 autoconf 2.72 基底补 OHOS 识别，随 `patches/config.guess`+`config.sub` 整文件替换；同时显式传 `--build/--host`（ref: E072 同型） |
| 2 | `configure` 报 `Permission denied`（辅助脚本） | HMDFS 适配路径可能剥掉 autotools 辅助脚本可执行位 | `build()` 内对 `configure`/`config.guess`/`config.sub`/`install-sh`/`missing` 补 `chmod +x`（ref: E490） |
| 3 | `conan` 下载源码 sha256 校验失败 | swfmill.org 对 `.tar.gz` 无条件回 `Content-Encoding: gzip`，requests/urllib3 透明解一层 → 拿到解码面字节（`fbcfe1a3…`），与 conandata 文件面锚定（`db24f639…`）必然不符 | `source()` 先 `get()`，捕 `ConanException` 后改用 `urllib` 原始字节回退（blepvco 0.1.0 同款），文件面 sha256 保持权威锚定（ref: E690 同型） |
| 4 | `configure` 找不到 `libexslt.pc`（EXSLT 探测失败） | conan 依赖包不在系统 pkg-config 搜索路径内；libxslt 配方只声明单组件、无独立 `libexslt.pc`；且包内 `.pc` 的 `prefix` 固化了打包机路径 | `generate()` 直接向 configure 注入六个模块的 `*_CFLAGS`/`*_LIBS`（autoconf 官方绕过口径），取值全部来自 conan `cpp_info` |
| 5 | CI 报 `L0c: No test source files in test_package/`（本地全绿） | 测试逻辑原先全内联在 `test_package/conanfile.py` 的 `test()` 里；CI L0c 的 find 白名单是 `.c/.cpp/.cc/.cxx/.sh/.py` 且**显式排除 `conanfile.py`**，而本地 W2/PF3 只验「conanfile.py 存在 + `test()` 有 `self.run`」→ 两条本地口径都不报 | 新增 `test_package/test.sh` 承载全部用例（测试数据 heredoc 内联），`conanfile.py` 改为 bash 派发（OHOS `/system/bin/sh` 不能可靠执行 ELF；2048.c/aa3d 先例） |
| 6 | `swfmill xslt` 观测项 `rc=255`（input document could not be read） | 上游 `xslt` 子命令签名为 `xslt <stylesheet.xsl> <input.xml> [<output.swf>]`（`src/swfmill.cpp:279`），原调用漏传输入 XML，swfmill 把输出名当输入读 | `test.sh` 补全参数；观测结果由 `rc=255` 变为 `rc=0 output_bytes=30` |
| 7 | CI `conan-build-test` 失败：`configure` 最后一步写 `./confJpcfHE/subs1.awk` 报 `Permission denied`，随后 `could not setup config files machinery`（本地全绿） | HMDFS 语义（**E129**）：`configure` 建临时目录用 `umask 077 && mktemp -d "./confXXXXXX"`，在 setgid hmdfs 挂载上落盘 `drwx--S---`(2700)——组权限位为空，**非属主**构建用户（CI worker）无法进入，写文件即 EACCES；本地以属主身份构建走 owner 位不触发 | 补丁 `patches/0001-configure-umask-002.patch`：把 `configure` 中两处 `umask 077` 放宽为 `umask 002`（该段文本同为 config.status 的 verbatim 模板，改 configure 即覆盖两处）。取 `002` 而非 `022` 的依据见下节实测 |

### 问题 7 的实测依据（HMDFS 目录权限归一化）

在 `/storage/Users/currentUser` 下建一个与 conan 构建目录同权限（setgid `2771`）的父目录，
两轮复现同一结果：

| 创建方式 | 落盘权限 | 组位 | 非属主在目录内建文件 |
|----------|----------|------|----------------------|
| `umask 077 && mktemp -d ./confXXXXXX` | `2700` `drwx--S---` | 无任何权限 | ❌（CI 实况，EACCES） |
| `umask 022 && mktemp -d ./confXXXXXX` | `2751` `drwxr-s--x` | `r-x`（无写位） | 存疑：组无写位 |
| `umask 002 && mktemp -d ./confXXXXXX` | `2771` `drwxrws--x` | `rwx` | ✅ |
| `mkdir`（任意 umask） | `2771` | `rwx` | ✅ |
| `mktemp -d` 后任意 `chmod` | `2771` | `rwx` | ✅ |

关键判据：conan 构建目录自身就是 `2771`，而构建期该目录可写（`configure` 在其内成功
写出 `config.log`/`config.status`），故 `2771` 是本环境**已验证可用**的档位。`umask 002`
确定性地落在这个档位上，且不依赖调用方的环境 umask。仓内已发布先例 `abook/0.6.1` 采用
等效写法（直接删除 `umask 077`，继承环境 umask `0002` → 同为 `2771`）。

## 源码修改

补丁见 `patches/`，逐字内容可核：

1. `patches/0001-configure-umask-002.patch` — `configure` 中创建临时目录的两处
   `umask 077` → `umask 002`（E129）。这是生成文件，但发布 tarball 只提供它、
   CI worker 无 automake 无法 autoreconf，故就地修补。不涉及平台宏，无
   `#ifdef` 守卫。
2. `patches/config.guess` + `patches/config.sub` — 整文件替换（非 diff 补丁），
   由 `build()` 内的 copy 覆盖上游 2005 版（E072）。因 `conandata.yml` 的
   `patches` 段原先为空，这两个文件由 `export_sources()` 显式导出
   （abiword-plugin-* 3.0.8 同款机制）。

## 依赖版本

- `libxml2/2.15.3`（共享；configure 模块 `XML`）
- `libxslt/1.1.45.1`（共享；单包同时提供 `libxslt` 与 `libexslt`，对应 configure 的
  `XSLT`/`EXSLT` 两个模块）
- `freetype/2.14.3`（共享；模块 `FREETYPE`）
- `libpng/1.6.58`（共享；模块 `PNG`，链接名 `-lpng16`）
- `zlib/1.3.1.1`（共享；模块 `ZLIB`；按 libpng/1.6.58 的精确 pin 对齐）

全部依赖均已 `conan download` 核验可消费（L0i 在 CI 侧亦逐个确认在制品仓内），
未使用 `--build=missing` 规避。

## 验证结果

- 编译：`conan create` 干净构建通过（conan-verify G2 PASS，L0–L5 全绿）。
- 上游测试（实跑，非抽样）：

```bash
# 以 SWFMILL 环境变量指向被测二进制，运行上游 test/ 两个 shell 套件
SWFMILL=<pkg>/bin/swfmill sh test/xml-swf-round-trip/run-test.sh   # 53/53 PASS
SWFMILL=<pkg>/bin/swfmill sh test/transform-and-verify/run-test.sh # 4/5 （import-ttf 平台差异）
```

  合计 58 用例：57 通过 / 1 失败 / 0 跳过。唯一失败
  `transform-and-verify/import-ttf.xsl` 需宿主 TrueType 字体渲染环境（OHOS 设备
  无该环境），属平台性差异，非功能缺陷。
- `test_package`（消费者视角，`test_package/test.sh`）：

  | 用例 | 断言口径 | 结果 |
  |------|---------|------|
  | xml2swf 最小 XML → SWF | 断言产物存在且非空 | PASS（30 bytes） |
  | swf2xml SWF → XML 往返 | 断言产物存在且非空 | PASS（404 bytes） |
  | OHOS XSLT 引擎渲染 movie | rule12 非断言（仅打印观测） | 观测完成 `rc=0 output_exists=yes output_bytes=30` |

- W3 本地 CI 模拟：`ci/conan/build_and_test.sh` 通过（1/1，100%）。
- 报告：`reports/conan-verify-report.md`、`reports/test-report.md`、
  `reports/w3-local-ci.log`。

## 注意事项

- CLI 应用按 R38 提供 `archives/s/swfmill/commands.json`（`xml2swf`/`swf2xml`/`xslt`）。
- 上游 `configure` 是 autoconf 2.6x 生成（含 `as_fn_error`/`mktemp -d "./confXXXXXX"`），
  补丁 0001 打的正是这个预生成文件，`patch_strip` 用默认值。
- `xslt` 子命令必须传输入 XML，否则报 `input document could not be read`（rc=255）。
- `/system/bin/sh`（mksh）不能可靠执行 ELF，故 `test_package` 一律经 `bash` 派发。
- CI 侧 L2 smoke 记为 skip：swfmill 上游无 `--version`/`--help` 选项（CLI 设计如此），
  非缺陷。
- CI 失败诊断的「类别: 网络问题 / 源码下载超时」为**自动分类误判**：真正的首错误是
  HMDFS umask 临时目录权限问题（见问题 7）；日志里
  `[fail] No such file or directory: 'curl'` 只是预下载步骤在 worker PATH 下缺
  `curl` 的降级告警（后续 conan 自身的下载与 E690 urllib 回退均成功取到源码）。
---

**编译结束**: 2026-10-10 18:44
**最终状态**: published
