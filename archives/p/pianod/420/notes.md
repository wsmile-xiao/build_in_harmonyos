# pianod 420 适配笔记

> 归档标识 `pianod`（任务书指定，与 `bin/pianod` 一致）；上游 r420 发布包名与 `AC_INIT([pianod2])` 为 **pianod2**，下文涉及上游文件名/宏时保留原名。
> 本任务 #9497（pianod 420）以 main 中已合入的 **421** 配方为范本做版本移植：r420 与 r421 相邻一版，ChangeLog 仅 `r420 (2025-12-28): Build with ffmpeg 8.`（本配方走 gstreamer 引擎，不受影响），四个补丁所涉及的 `config.guess / config.sub / pianod_unittest / callback_test.cpp` 两版逐字节相同。

## 编译环境
- 构建系统: autotools（configure + make + automake 生成的 TESTS）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15.0.4（OHOS NDK 26.0.0.18，aarch64-linux-ohos）
- Conan: 2.29.1（OHOS 适配版），profile `ohos-aarch64`（os=OHOS os.version=6.0 arch=armv8）
- 独立 CONAN_HOME：`~/work/psj/ch-pianod`（镜像 `~/.conan2` 的 remotes/settings/profiles，仅隔离包缓存，不污染共享缓存；与并行会话互不干扰）

## 上游与目标

| 项 | 值 |
|---|---|
| 软件 | pianod2（用户任务书写作 "pianod"，r420；`pianod` 是本项目 r1 旧代） |
| 官方发布源 | https://deviousfish.com/Downloads/pianod2/pianod2-420.tar.gz（SVN 项目，无 GitHub/GitLab 镜像） |
| sha256 | 9fa739cf28d5f554d982acecb94857b9fe0d0fd839d238dfca90f143c9fab216（本地 `sha256sum` 与真机 `source()` 下载双向核对一致） |
| 变更（ChangeLog r420, 2025-12-28） | Build with ffmpeg 8（本配方走 gstreamer 引擎，无感知） |
| 许可 | MIT（COPYING） |

## 选型依据（configure 的三态开关，见 configure.ac）

pianod2 的依赖全部是"三态可选"（yes/no/check），构建期只强制两件事：
1. **至少一个媒体引擎**（`AC_MSG_ERROR([There is no media engine available])`）
2. **crypt + 系统头 + C++14**

选定的最小可行组合（与 421 一致，全部命中制品仓预编译包）：

| 维度 | 选择 | 理由 |
|---|---|---|
| 媒体引擎 | `--with-engine=gstreamer` | gstreamer 自带音频输出，可完全避开 libao/libsdl/libavdevice；ffmpeg 分支会额外引入 13 个传递依赖 |
| TLS | `--with-tls=openssl` | 与 curl/8.15.0.1 的 pin（openssl/3.5.6.1）对齐，避免版本冲突 |
| HTTP 客户端 | `curl/8.15.0.1`（**不是** `libcurl/8.5.0`） | 见下"问题 #5" |
| 元数据 | `taglib/1.13.1` | filesystem source 读 ID3；`tagreader` 是上游测试之一 |
| 压缩 | `zlib/1.3.1.1` | override 归一 glib2/taglib 与 curl 的 zlib pin |
| 终端 | `ncurses/6.6` | 失败计数彩色输出；见"问题 #6" |
| 放弃 | libwrap / PAM / libbsd / SDL1.2 / libao | 制品仓无包，且 configure.ac 对全部做了 `DF_DO_WITHOUT` 自动降级 |

## R51 上游测试申报表（适配前清点 → 实际执行 → 回填）

清点方法：`grep -rn "^TESTS" Makefile.am src/*/Makefile.am src/*/*/Makefile.am`（automake 注册项，共 **7** 个用例，无 tests/ 目录、无 ctest）。真机 `conan create` 的 `build()` 内 `make check` 实测（与 CI 同源）：

| # | 用例（TESTS 注册名） | 所在目录 | 实跑结果 |
|---|---|---|---|
| 1 | callback_test | src/common | PASS（进程级） |
| 2 | utility_test | src/common | PASS（`43 tests run: 43 passed`） |
| 3 | parsnip_test | src/parsnip | PASS（`Tests performed: 415`，passed 414 / skipped 1） |
| 4 | parsnip_test_2 | src/parsnip | PASS（`Tests performed: 442`，passed 441 / skipped 1） |
| 5 | tagreader | src/mediaunits/metadata | PASS（进程级：以 cookies.mp3 走 taglib 读取路径，无内建计数器） |
| 6 | blowfish_test | src/mediaunits/pandora | PASS（34 组加密向量 `All tests passed.`） |
| 7 | pianod_unittest | 顶层 | SKIP（`exit status: 77`，原因见"问题 #7"） |

test-driver 汇总：`PASS: callback_test / utility_test / parsnip_test / parsnip_test_2 / tagreader / blowfish_test` + `SKIP: pianod_unittest`；各 `test-suite.log` 一律 `# FAIL: 0 # XFAIL: 0 # ERROR: 0`。

实测统计：**用例级** TOTAL 7 / PASS 6 / SKIP 1 / FAIL 0；**断言级合计 934**（43 + 415 + 442 + 34，逐项均可在构建日志 `[upstream-test]` 行 grep 到原文）。计数口径与 421 完全一致（r420/r421 源码同测试集）。

test_package 运行时验证：`Checks run: 15, passed: 15, skipped: 0`（10 项依赖链接/自省断言 + 5 项 live daemon 断言，详见下文 R40）。

## 遇到的问题与解决方案（跨 r420/r421 通用，本 420 构建逐条复现）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type` | OHOS `uname -s` 返回 `HarmonyOS`，GNU config 无此分支（知识 E160/E007） | 补丁 0001：产出 `aarch64-unknown-linux-ohos` |
| 2 | `config.sub ... Kernel 'linux' not known to work with OS 'ohos'` | config.sub 末尾内核-OS 兼容校验表缺 `linux-ohos`（E268） | 补丁 0002：登记 `linux-ohos*` |
| 3 | `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS：`mktemp -d` 产出 owner 也无法写入的 0700 目录（E114） | 配方生成 POSIX mktemp shim 前置 PATH + 短路 mktemp 分支 |
| 4 | `use of undeclared identifier 'rpl_malloc'` | `AC_FUNC_MALLOC` 交叉环境默认 no，替换为不存在的 gnulib rpl_malloc | configure 传缓存 `ac_cv_func_malloc_0_nonnull=yes ac_cv_func_realloc_0_nonnull=yes` |
| 5 | Pandora 运行期需 HTTPS，但制品仓 `libcurl/8.5.0` 不可用 | 该配方 `CURL_USE_OPENSSL=OFF` | 改用 `curl/8.15.0.1`（`CURL_USE_OPENSSL=True`） |
| 6 | `ld.lld: unable to find library -lncurses` | ohpcd ncurses 只发布宽字符库，`m4/dfcheckncurses.m4` 硬编码 `-lncurses` | 配方生成窄字符库别名（`libncurses.a ← libncursesw.a` 等 4 个） |
| 7 | `FAIL: pianod_unittest`（No such file or directory） | 脚本 shebang `#!/bin/ksh`，OHOS 无 `/bin/ksh` | 补丁 0003：shebang 改 `#!/bin/sh`，保留上游 ksh93 守卫 → 以 exit 77 上报 SKIP（本 420 实测 `SKIP: pianod_unittest (exit status: 77)`） |
| 8 | zlib 版本冲突（glib2/taglib pin 1.3.1 vs curl pin 1.3.1.1） | 传递依赖 pin 不一致 | 配方 `self.requires("zlib/1.3.1.1", override=True)` 归一 |
| 9 | `configure: error: Media engine gstreamer not found`（链接缺 glib 符号） | gstreamer 配方未设 `pkg_config_name`，产物 `gstreamer.pc` 而非 `gstreamer-1.0.pc` | 配方生成 `gstreamer-1.0.pc` 别名（保留 `Requires: glib-2.0`） |
| 10 | `src/common/callback_test.cpp:13: error: invalid preprocessing directive` | **上游 typo** `#undefine NDEBUG`（Release `-DNDEBUG` 时必现） | 补丁 0004：`#undefine` → `#undef`（本 420 源码 line 13 同样命中，补丁 `git apply --check` 通过） |
| 11 | 打包产物埋进嵌套路径 | `Autotools.install()` 以 `DESTDIR=<pkg>` 调 `make install`，绝对 prefix 会嵌套 | prefix 配 `/`，得 `<pkg>/bin`、`<pkg>/share` |
| 12 | `cannot run C compiled programs` | `AutotoolsDeps` 把 shared 依赖注入 autoconf 运行期探测 | 去掉 `AutotoolsDeps`，改 `PkgConfigDeps` + build() 导出 `LD_LIBRARY_PATH` |
| 13 | `httpclient.h: fatal error: 'curl/curl.h' file not found`（构建 `http_test`） | `Makefile.am` 只对 `pianod` 目标转发依赖 include | 把依赖 includedirs 注入 `tc.extra_cflags/extra_cxxflags`（本次构建日志可见 curl/gstreamer/taglib/ncurses 等 `-I` 已烘入各目标） |

## 源码修改（补丁与 421 逐字节相同）

| 文件 | 修改 | 性质 |
|---|---|---|
| `config.guess` | 增加 `*:HarmonyOS:*:*` 分支，产出 `${MACHINE}-unknown-linux-ohos` | autotools 探测脚本，OHOS 标准做法（E007/E160） |
| `config.sub` | 增加 `ohos` OS 白名单 + `linux-ohos` 内核兼容项 | 同上（E268） |
| `pianod_unittest` | shebang `/bin/ksh` → `/bin/sh`（1 行） | 让上游 ksh93 守卫以 SKIP 上报；未改测试逻辑 |
| `src/common/callback_test.cpp` | `#undefine NDEBUG` → `#undef NDEBUG`（1 词） | 上游 typo，Release 构建必现失败 |

补丁不含 `__OHOS__` 平台宏、不含明文 `http://`、不含第三方镜像。四个补丁已用 `git apply --check -p1` 验证可干净应用于 pianod2-420 源码树。

## 验证结果（真机 `conan create`，独立 CONAN_HOME=~/work/psj/ch-pianod）

```bash
$ conan create archives/p/pianod/420 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# 8 个依赖全部命中制品仓预编译包（curl/8.15.0.1 openssl/3.5.6.1 gstreamer/1.28.3 taglib/1.13.1
#   ncurses/6.6 zlib/1.3.1.1 glib2/2.88.0 pcre2/10.45），仅 pianod/420 自身从源码构建
# 配方内 make check 实录：
#   PASS: callback_test   PASS: utility_test   PASS: parsnip_test   PASS: parsnip_test_2
#   PASS: tagreader       PASS: blowfish_test  SKIP: pianod_unittest (exit status: 77)
#   各 test-suite.log: # FAIL: 0  # XFAIL: 0  # ERROR: 0
#   utility 43/43 | parsnip 415(414+skip1) | parsnip_2 442(441+skip1) | blowfish 34 → 断言合计 934
# test_package:
#   RUN: pianod -v   →  pianod2 version 420
#   RUN: ./test_pianod →  Checks run: 15, passed: 15, skipped: 0 / All tests passed.
#   （含 5 项 R40 运行时：真起守护进程 → TCP 连接 → 行协议 200 Success →
#     "live daemon reports upstream r420" → Privileges/SelectedSource）
CREATE_EXIT:0
```

### R40 多媒体运行时结论（与 421 一致）

打包后的 `pianod` 以 `-c <pkg>/share/pianod/html -p <port> -P 0 -s 0 -T` 启动后，网络服务、会话与权限协商、媒体管理器（manager/Pianod 虚拟源）在 OHOS 上真实工作（test_package 的 5 项握手断言全绿）。但音频**播放链路**受 gstreamer 插件生态限制不可用：制品仓 `gstreamer/1.28.3` 只发布核心静态库，不含 `appsrc`/`playbin`/sink 等运行时插件 `.so` 与 registry，属依赖生态缺口（已在 421 登记为系统能力需求），非本包代码缺陷——构建、链接、服务、协议、元数据、加密各层均已验证通过。

### 已知限制（跨版本通用）

1. **`piano` / `runmix` 在 OHOS 上不可直接执行**：二者是 `#!/bin/ksh` 脚本，重度依赖 ksh93 内建；OHOS 生态无 ksh93。未擅自改写（功能级移植，风险高于收益），主用途（网络协议 + Web 客户端）不受影响。
2. **Web 客户端目录**：因 `make install` 走 `DESTDIR=<pkg>`、prefix 只能为 `/`，编译期固化的 `DEFAULT_WWWDIR` 为 `//share/pianod/html` 不可用；配方通过 `runenv_info.define_path("PIANOD_CLIENTDIR", …)` 暴露真实路径，`pianod -c "$PIANOD_CLIENTDIR"` 即可（test_package 运行时用例即走此路径完成握手）。
3. **Pandora 功能需要账号**（`PANDORA_USER`/`PANDORA_PASSWORD`）。

## 本次会话记录 [2026-09-19]

- 任务 #9497（pianod 420，`taskBranch=feat/pianod-420`，claimer=iKalous_OscarP）已由本队领取；main 已合入 421（另一版本，不触发 R37），制品仓仅有 421 无 420。
- 以 421 为范本移植 420：独立下载 pianod2-420.tar.gz，`sha256=9fa739cf…fab216`（真机 `source()` 下载字节数 916642 与本地一致，双向核对）；`git apply --check -p1` 验证 4 补丁均可干净应用；确认 `configure` 内 `PACKAGE_VERSION='420'`，banner 宏 `PACKAGE " version " PACKAGE_VERSION` 产出 `pianod2 version 420`。
- 真机 `conan create` 全绿：`CREATE_EXIT:0`，上游 `make check` 6 PASS / 1 SKIP / 0 FAIL（断言合计 934），消费者 15/15。
