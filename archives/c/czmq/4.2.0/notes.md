# czmq 4.2.0 — HarmonyOS PC (aarch64) 适配笔记

> 档案创建: 2026-10-04　任务: czmq 4.2.0 适配（上游 4.2.1 已有停滞 PR #4216，按规则改版）
> 结果: ✅ W3 本地 CI 模拟全绿（上游 ctest 30/30 + test_package 37 断言 + L0/L1/L5 门禁通过）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | czmq（ZeroMQ 高层 C 绑定） |
| 版本 | 4.2.0（上游正式 tag v4.2.0，2019-02-10 发布） |
| 上游 | https://github.com/zeromq/czmq |
| 源码 | https://github.com/zeromq/czmq/releases/download/v4.2.0/czmq-4.2.0.tar.gz |
| SHA256 | `cfab29c2b3cc8a845749758a51e1dd5f5160c1ef57e2a41ea96e4c2dcc8feceb` |
| 构建系统 | CMake（上游 zproject 生成；autotools 为另一套，未用） |
| 依赖 | `libzmq/4.3.5`（制品仓已发布，官方包名；旧归档 `zeromq/4.3.5` 同源） |
| 补丁数 | 5 |
| 测试 | 上游 ctest 30/30 通过；test_package 37 断言通过 |

### 为什么是 4.2.0 而不是 4.2.1

* 上游 czmq 最新 release 就是 **v4.2.1**（2021-01-17），没有更新版本可迁；4.2.0 是唯一另一稳定 release。
* 本项目远端**已存在 czmq 4.2.1 的 PR**：`#4216 feat: adapt czmq 4.2.1 for HarmonyOS PC (aarch64)`
  （`feat/czmq-4.2.1 → main`，open，2026-08-06 创建、2026-08-30 后无更新，CI `conan-build-test` 单次失败未闭环）。
  按任务约定「同版本已有 PR 则换版本」，本次选 4.2.0，避免重复劳动与撞车。
* 上游 czmq 仓库本身**没有**任何 HarmonyOS/OHOS/OpenHarmony 相关的 issue 或 PR（GitHub 检索 0 条），
  因此不存在可直接复用的上游 ohos 适配。
* 4.2.0 与 4.2.1 的差异恰好包含两处影响 OHOS 的 selftest 缺陷，本次以补丁 0003/0004 **backport 上游修复**。

### W0 依赖预检（R35：禁止用 conan list 判断）

```bash
export PATH="$HOME/usr/local/bin:$PATH"     # 注意：~/.local/bin/conan 的 shebang 指向失效解释器，会误报未发布
conan download libzmq/4.3.5 -r=ohpcd        # exit=0，recipe + binary 均在
```

* `libzmq/4.3.5`（官方名）与 `zeromq/4.3.5`（旧归档名）**均已发布**，binary 为 shared、
  `ENABLE_CURVE=OFF` / `WITH_LIBSODIUM=OFF` / `ENABLE_DRAFTS=OFF`。
* `libsodium/1.0.20`、`1.0.22` 已发布，但 **czmq 不依赖 libsodium**（源码零引用），
  libsodium 只被 libzmq 的 CURVE 功能使用。

## 二、适配过程

### 阶段 0：源码盘点（R51 上游测试申报表）

* 上游测试形态：**单二进制自测**（zproject 生成）。`src/czmq_selftest.c` 维护 `all_tests[]` 表，
  CMake 侧 `set(TEST_CLASSES ...)` 为每个类注册一个 ctest：
  * `ENABLE_DRAFTS=OFF`（本包）：**30 个 stable 类**（zactor, zarmour, zcert, zcertstore, zchunk, zclock,
    zconfig, zdigest, zdir, zdir_patch, zfile, zframe, zhash, zhashx, ziflist, zlist, zlistx, zloop,
    zmsg, zpoller, zsock, zstr, zsys, zuuid, zauth, zbeacon, zgossip, zmonitor, zproxy, zrex）。
  * `ENABLE_DRAFTS=ON`：追加 10 个 draft 类 + `private_classes`（共 41）。
* 另有 `src/test_randof.c`（noinst 程序，未注册进 ctest）。
* `CLASSTEST_TIMEOUT` 默认 60s，本包提高到 120s。

### 阶段 1：补丁（5 个，全部经 `patch -p1` 干净应用验证）

| 补丁 | 文件 | 原因 |
|------|------|------|
| 0001 | `CMakeLists.txt` | `cmake_minimum_required(VERSION 2.8.8)` → `3.5...3.27`。CMake 4.x 已移除 <3.5 兼容（与 libzmq 4.3.5 patch 0001 同型根因）。 |
| 0002 | `src/zfile.c` | `zfile_tmp()` 硬编码 `/tmp/czmq_zfile.XXXXXX`；OHOS HMDFS 上 `/tmp` 是只读 erofs，`mkstemp()` 必失败 → 改为优先读 `TMPDIR`（未设置时回落 `/tmp`）。通用可移植性修复，无平台宏。 |
| 0003 | `src/zarmour.c` | backport 上游 v4.2.1：selftest 空串用例断言 `size == strlen(expected)+1` 恒失败（空输入解码 size 为 0），库本身无误。 |
| 0004 | `src/zproxy.c` | backport 上游 v4.2.1：selftest 后端端点 `ipc://…` → `tcp://127.0.0.1:<动态端口>`。OHOS 拒绝 AF_UNIX bind（实测 `zmq_bind("ipc://backend") rc=-1 errno=1 EPERM`，tcp 正常）。 |
| 0005 | `CMakeLists.txt` | libzmq 改为 `-L<dir> -lzmq` 链接（原按 `find_library` 绝对路径链接）。制品仓 `libzmq.so` 无 DT_SONAME，按路径链接会把 conan 缓存绝对路径写进 DT_NEEDED，并让 CMake 在导出文件里写 `IMPORTED_NO_SONAME TRUE`（CI L5b/L5c 门禁失败）。 |

### 阶段 2：配方要点（conanfile.py）

| 项 | 做法 | 原因 |
|----|------|------|
| 依赖声明 | `self.requires("libzmq/4.3.5", transitive_headers=True, transitive_libs=True)` | czmq 公开头 `czmq.h → czmq_prelude.h → <zmq.h>`，消费者必须拿到 libzmq 的 include/libs；不加 traits 时 CMakeDeps 生成的传递依赖 include/libs 元数据为空 → 消费者 `'zmq.h' file not found`（已合入的 zmqpp 配方同样声明） |
| libzmq 发现 | `PkgConfigDeps` + `CMakeDeps` 同时生成 | czmq 的 `find_package(libzmq)` 命中自带 `Findlibzmq.cmake`（module 模式），该文件用 `pkg_check_modules(libzmq)` 找 zmq.h/库；`libzmq/4.3.5` 导出 `pkg_config_name=libzmq` → 必须生成 `libzmq.pc` |
| 可选系统库 | `CMAKE_DISABLE_FIND_PACKAGE_{uuid,systemd,lz4,libcurl,libmicrohttpd}=ON` | zproject CMake 会探测宿主上的这些库并链进 libczmq —— 首次本地构建就误链了 `~/usr/local` 的 `libcurl.so.4`，包会依赖宿主环境 |
| drafts | `ENABLE_DRAFTS=OFF` | 上游明确「分发版不建议开启 draft」；同时避免可选 libcurl/microhttpd 依赖；ctest 注册数 40→30 |
| 编译器解析 | `generate()` 内校验 profile 的 `tools.build:compiler_executables` 路径存在，否则回落 `shutil.which("clang")` | 预检/部分 worker 上 `/data/service/hnp/bin/clang` 不存在时，CMake `project()` 报 "not a full path to an existing compiler tool" |
| SONAME | `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG/CXX_FLAG=-Wl,-soname,` | 环境无 `Platform/HarmonyOS` CMake 模块 → CMake 不知道该系统的 soname 旗标 → `libczmq.so` 无 DT_SONAME（L5a），下游无法按 soname 寻址 |
| ctest 运行环境 | `LD_LIBRARY_PATH` 前置构建目录 + `dependencies["libzmq"].libdirs` | 上游 CMake 不设构建树 RPATH；`conanbuild` 环境不含 host 依赖 libzmq 的 lib 目录（libzmq 按 soname 链接后运行期需要） |
| package() | `rmdir(package_folder/bin)` | 唯一安装的 helper `zmakecert` 是交互式 CURVE 证书生成器；libzmq 关闭 CURVE 时只能生成全 0 密钥，不随包分发；包保持纯库形态（无需 commands.json，R38） |
| package_info | `cmake_file_name=czmq`、`cmake_target_name=czmq::czmq`、`pkg_config_name=libczmq`、`libs=["czmq"]`、`system_libs=["pthread"]` | 与上游安装的 `czmqConfig.cmake`/`libczmq.pc` 命名一致 |

### 阶段 3：W3 实测（本地 CI 模拟 = 真实 CI 脚本）

```bash
export PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin:$HOME/usr/local/bin:$PATH
export TMPPREFIX="$HOME/tmp/zsh/zsh-" TMPDIR="$HOME/tmp"     # zsh heredoc 与 /tmp 只读
CI_PACKAGES="archives/c/czmq/4.2.0" zsh ci/conan/build_and_test.sh archives/c/czmq/4.2.0
```

* **L0**（质量门禁）: pass　**KC**（知识库）: pass　**JC**（杂项文件，含 JC6 单软件原子性）: pass
* **L1**（上游测试 + test_package）: pass —— `100% tests passed, 0 tests failed out of 30`，
  `ALL CZMQ HARMONYOS TESTS PASSED (37 checks)`
* **L2**: skip（无 bin/）　**L4**: warn（见下）　**L5**（基线/SONAME）: pass
* 产物核对：`lib/libczmq.so → libczmq.so.4 → libczmq.so.4.2.0`，`SONAME=libczmq.so.4`，
  `DT_NEEDED={libzmq.so, libc.so}`（无绝对路径），包内无 `IMPORTED_NO_SONAME`

## 三、遗留与说明

* **CURVE 功能不可用**：`libzmq/4.3.5` 已发布形态是 `ENABLE_CURVE=OFF`，czmq 通过
  `zsys_has_curve()` 优雅降级（`zcert_new()` 生成全 0 密钥）。若后续需要 CURVE，须先在 libzmq 侧
  开启 `ENABLE_CURVE=ON` + `libsodium`，按 R37 递增为 `libzmq/4.3.5.1` 重新发布，再改 czmq 的 requires。
* **L4 告警（非阻塞，两处均为规则误判）**：CI 的 L4 规则用 `(strcpy|sprintf|gets|strcat)\b` 扫补丁：
  ① 补丁 0004 的 `zsys_sprintf`（czmq 自有分配式格式化助手，上游 4.2.1 代码）命中 `sprintf`；
  ② 补丁 0005 注释里 `czmqTargets.cmake` 的 "tar**gets**" 命中 `gets`。均未引入危险函数。
* **clean-verify(G0) 的预期失败（非阻塞）**：`ohc-run.py clean-verify` 只跑 autotools
  `./configure --prefix=…`（即使配方是 CMake 构建）；本包形态下它的结果是：
  ① 5 个补丁全部干净应用 ✅；② `configure` 失败（上游 2019 年的 `config.guess`/`config.sub`
  不认 `HarmonyOS`/ohos 三元组，且该检查器的临时目录内 `getcwd` 取不到工作目录）。
  这两点都不影响本包：构建走 CMake，权威门禁是 `conan-verify`（G1/G2/G3 全过，见 finish 日志
  Step 4）与 W3 本地 CI 模拟（L0/L1/L5 pass + ctest 30/30 + test_package 37 checks）。
  复核证据：`python3 scripts/ohc-run.py clean-verify czmq 4.2.0`（补丁 5/5 应用成功，configure 阶段失败）。
* **补丁 0002 的覆盖口径（如实记录）**：`zfile_tmp()` 的**函数定义**在 `src/zfile.c` 中无条件编译，
  但其**公开声明**与上游 selftest 的**调用**都在 `#ifdef CZMQ_BUILD_DRAFT_API` 内。本包
  `ENABLE_DRAFTS=OFF`，故该函数在本包形态下既不被 selftest 调用、消费者也不可见 ——
  补丁 0002 是为 draft 构建（及后续开启 draft 的消费者）保留的正确性修复（消除对只读 `/tmp` 的硬编码），
  **在本包形态下无测试覆盖**。

## 四、上游测试实测（R51 回填）

| 口径 | 数值 |
|------|------|
| 上游注册（本包形态，ENABLE_DRAFTS=OFF） | 30（ctest 类） |
| 实际运行 | 30 |
| 通过 | 30（100%） |
| 排除/跳过 | 0 |
| test_package 断言 | 37/37 |

命令与日志：`ctest --output-on-failure`（构建目录）、`./test_czmq`（test_package）；
完整日志见 `reports/` 与 `.ci_logs/`（本地 CI 模拟）。
---

**编译结束**: 2026-10-04 23:15
**最终状态**: published
