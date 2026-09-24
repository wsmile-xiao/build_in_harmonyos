# libideviceactivation 1.1.1 适配笔记

## 编译环境

- 构建系统: autotools（autoconf ≥2.64 / automake / libtool；tarball 自带预生成 `configure`）
- 编译日期: 2026-09-22
- 编译器: clang / clang++（`/data/service/hnp/bin/clang`，clang 15.0.4，target `aarch64-unknown-linux-ohos`）
- 目标平台: OHOS / HarmonyOS PC（os=OHOS os.version=6.0 arch=armv8 compiler=clang 15 libc++ cppstd=17 Release）
- 状态: built

## 编译步骤

```bash
# 1) 初始化（下载 + 解压 + 归档骨架 + 依赖解析）
python3 scripts/ohc-run.py init-build libideviceactivation 1.1.1 \
  --url=https://github.com/libimobiledevice/libideviceactivation/releases/download/1.1.1/libideviceactivation-1.1.1.tar.bz2 \
  --tar=tar.bz2 --auto

# 2) 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight libideviceactivation 1.1.1 --src "$BUILD_SRC_DIR"
# → task=cpp, detected=c（c↔cpp 兼容族）→ 继续

# 3) 依赖准备（PkgConfigDeps 生成 .pc；不使用 AutotoolsDeps，避免把共享依赖
#    塞进 LIBS 导致 configure 的 conftest 运行期 "Error loading shared library libcurl.so"）
conan install .libideviceactivation/deps2 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 -of .libideviceactivation/deps2/out --build=never

# 4) 真实编译（探索阶段人工命令；对应配方 generate()/build() 的 shim）
source .libideviceactivation/deps2/out/conanbuild.sh
export PATH=<mktemp-wrapper-dir>:$PATH          # OHOS-2
cd $BUILD_SRC_DIR
./configure --build=aarch64-unknown-linux-gnu --prefix=$DEFAULT_PREFIX   # OHOS-1
make -j1                                                                 # OHOS-3 前置：依赖 .la 改名
make install DESTDIR=$TEST_PREFIX
make check
```

## 遇到的问题与解决方案

| # | 问题（真实报错） | 根因 | 解决方案 | 知识条目 |
|---|------|------|----------|----------|
| 1 | `configure: error: cannot guess build type`；`./config.guess` rc=1，`unable to guess system type`（`uname -s = HarmonyOS`，`uname -r = HongMeng Kernel 1.12.0`） | 上游 `config.guess` 时间戳 2018-03-08，不认识 HarmonyOS | 显式 `--build=aarch64-unknown-linux-gnu`（原生构建，不传 `--host`/`--target`；上游 `config.sub` 也不识别 `ohos` 三元组，传了会报 `Invalid configuration 'aarch64-linux-ohos': system 'ohos' not recognized`） | E007 / E160 / E072 |
| 2 | `Error loading shared library libcurl.so: (needed by ./conftest)` → `configure: error: cannot run C compiled programs`（首次尝试即失败） | 若使用 `AutotoolsDeps` 生成器，`LIBS` 会包含 `-lcurl -lxml2 …`，configure 最早的 `AC_PROG_CC` 运行探测就会链接整条共享依赖闭包，而 OHOS 加载器无 conan 缓存 lib 的默认搜索路径 | 配方**只用 `PkgConfigDeps`**（`configure.ac` 本就以 pkg-config 探测依赖），不引入 `AutotoolsDeps`；`PKG_CHECK_MODULES` 只做链接测试、不运行 conftest | E467 |
| 3 | `./config.status: line 878: ./confXXXXXX/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery`（configure rc=1） | HMDFS 上 `umask 077 && mktemp -d` 生成 **mode 2700 (`drwx--S---`)** 目录，**属主亦不可写**（实测 `touch` → Permission denied）；`umask 077 && mkdir` 则被 HMDFS 归一为 **mode 2771 (`drwxrws--x`)**，可写 | `generate()` 注入恒定 `exit 1` 的 `mktemp` wrapper 并前置 `PATH`，迫使 autoconf / `config.status`（L848-L855）走 `(umask 077 && mkdir)` 回退分支 | E011 / E114 / E129 |
| 4 | `libtool: error: '//lib/libplist-2.0.la' is not a valid libtool archive`（make rc=2） | 依赖包以 `--prefix=/` 发布：`.la` 内 `libdir='//lib'`，`dependency_libs` 含构建机绝对路径 `/storage/.../conan2/p/...`；本库用 libtool 构建且链接时优先解析 `.la` | `build()` 开头把各依赖 `lib/*.la` 改名 `*.la.bak`，使 libtool 回退到 `-L<dir> -l<name>`（同族 ideviceinstaller/1.2.0 先例） | E236 |
| 5 | `test.c: fatal error: 'plist/plist.h' file not found`（test_package 消费者编译失败） | Conan 2.29 的 CMakeDeps 对**非直接（传递）依赖**生成的 `<pkg>_INCLUDE_DIRS` 为空；且本包默认静态库，CMake 对静态库的传递依赖按 `$<LINK_ONLY:>` 处理、不传播 include | 配方 `requirements()` 对四个依赖声明 `transitive_headers=True`；`test_package/CMakeLists.txt` 显式链接上游依赖 target | E216 / E480 / E447 |

## 源码修改

无。三处适配全部为构建期 shim（`--build` 三元组 / `mktemp` wrapper / 依赖 `.la` 改名），
`conandata.yml` 的 `patches: []` 为空，未改动上游任何源码文件。

## 依赖版本

| 类型 | 依赖 | 版本 | 来源 |
|---|---|---|---|
| 直接强制 | libimobiledevice | 1.3.0 | configure.ac L21/L39（`>= 1.3.0`） |
| 直接强制 | libplist | 2.3.0 | configure.ac L22/L40（`>= 2.2.0`） |
| 直接强制 | libcurl | 8.5.0 | configure.ac L23/L41（`>= 7.20`） |
| 直接强制 | libxml2 | 2.15.3.1 | configure.ac L24/L42（`>= 2.9`） |
| 传递 | libusbmuxd | 2.0.2 | libimobiledevice/1.3.0 requires |
| 传递 | openssl | 1.1.1w | libimobiledevice/1.3.0 requires |
| 传递 | zlib | 1.3.1.1 | libcurl/8.5.0 requires |
| 系统 | libc / libpthread / libdl / libm | 工具链 sysroot | `AX_PTHREAD` + `AC_CHECK_LIB(pthread, pthread_once)` |

W0 可消费性：以上 7 个第三方依赖（配方级 + OHOS/armv8/clang 二进制级）`conan download` 全部 rc=0。

## 上游测试入口（R51 申报表）

| 项 | 实测结果 |
|---|---|
| `tests/` 目录数 | **0**（tarball 44 条目，`find . -iname "*test*"` → 0 条） |
| ctest 注册数 | 不适用（非 CMake 工程） |
| pytest 注册数 | 不适用（非 Python 工程） |
| automake 测试注册数 | **0**（`grep -rn "TESTS\|check_PROGRAMS\|check-local" */Makefile.am` → 无输出） |
| `make check` 实测 | rc=0，各子目录均 `Nothing to be done for 'check'.`（空操作） |
| 上游可执行入口 | `ideviceactivation` CLI（`man/ideviceactivation.1`）：`activate` / `deactivate` / `state`，**均需真实 iOS 设备 + usbmuxd** |

无设备环境下实测：`state` / `activate` / `deactivate` 均输出 `ERROR: No device found!` 且 rc=1；
`--version` 输出 `ideviceactivation 1.1.1` rc=0；`--help` rc=0。
因此上游**不存在可自动化的测试用例**，`make check` 不能作为质量门禁；质量保证由 `test_package/`
承担（`test_package/test.c` 15 条 API 断言 + `conanfile.test()` 2 条鸿蒙特有断言，共 **17 条**；
其中鸿蒙特有用例 **5 条**：`ohos_elf_interp`、`ohos_runtime_closure` + test.c 的 sysname/machine/指针宽度）。

## 验证结果

```bash
# configure / make / install（探索阶段实测）
./configure --build=aarch64-unknown-linux-gnu --prefix=$DEFAULT_PREFIX   # rc=0
make -j1                                                                 # rc=0
make install DESTDIR=$TEST_PREFIX                                        # rc=0
make check                                                               # rc=0（空操作）

# 产物
$TEST_PREFIX$DEFAULT_PREFIX/bin/ideviceactivation --version
#   ideviceactivation 1.1.1        (rc=0)
$TEST_PREFIX$DEFAULT_PREFIX/bin/ideviceactivation --help                   # rc=0
$TEST_PREFIX$DEFAULT_PREFIX/bin/ideviceactivation state
#   ERROR: No device found!         (rc=1，无设备）

# NEEDED（证明 OHOS 侧共享依赖闭包）
llvm-readelf -d .../bin/ideviceactivation | grep NEEDED
#   libideviceactivation-1.0.so.2 / libcurl.so / libxml2.so.16 / libc.so

# 配方层（conan create / conan-verify / finish）
#   见 reports/ 与 .ci-result.json
```

## 日志路径（本地证据）

| 日志 | 内容 |
|---|---|
| `.libideviceactivation/logs/01_init-build.log` | init-build（下载/解压/骨架/依赖/环境检查） |
| `.libideviceactivation/logs/02_lang-preflight.log` | R47 语言预检 |
| `.libideviceactivation/logs/10_first_error_configure.log` | 首个真实错误（baseline configure） |
| `.libideviceactivation/logs/11_first_error_configlog_evidence.log` | config.log 中 conftest 失败原文 |
| `.libideviceactivation/logs/12_fix1_configure.log` | 修复 1 后 configure |
| `.libideviceactivation/logs/13_probe_tmpdir_perms.log` | HMDFS `mktemp -d` vs `mkdir` 权限实测 |
| `.libideviceactivation/logs/14_fix2_configure.log` | 修复 2 后 configure rc=0 |
| `.libideviceactivation/logs/15_first_make.log` | libtool `.la` 报错原文 |
| `.libideviceactivation/logs/16_fix3_make.log` | 修复 3 后 make rc=0 |
| `.libideviceactivation/logs/18_make_install.log` | make install + 安装树 |
| `.libideviceactivation/logs/19_installed_tree.log` | 产物清单 + ELF NEEDED/SONAME |
| `.libideviceactivation/logs/21_cli_smoke.log` | CLI `--version` / `--help` / `state` |
| `.libideviceactivation/logs/22_make_check.log` | `make check` 实测 + 测试注册核验 |
| `.libideviceactivation/logs/23_upstream_cli_all_commands.log` | 上游全部 CLI 子命令实测 + man page |
| `.libideviceactivation/logs/25_proto_test.log` | test_package 测试程序原型编译/运行 |

## 注意事项

- `libxml2` 的 SONAME 为 `libxml2.so.16`，与 OHOS SDK 工具链自带
  `ohos-sdk_26.0.0.18/ohos/native/llvm/lib/libxml2.so.16`（libxml2 2.14.0）**同名**。
  运行期依赖搜索顺序必须保证 Conan 包 `lib/` 优先；`test_package` 的
  `ohos_runtime_closure` 用例对此做端到端校验。
- 默认 `shared=False`（静态库），与同族 libplist / libusbmuxd / libimobiledevice 保持一致。
- CLI 动态链接 `libcurl.so` 与 `libxml2.so.16`（二者在 ohpcd 仅以 shared 形态发布）。
  OHOS 加载器无 Conan 缓存 `lib/` 的默认搜索路径 → 直接执行需 `LD_LIBRARY_PATH`
  （即 Conan `conanrun` / `VirtualRunEnv` 环境）。本地 CI 的 L2 裸跑
  `ideviceactivation --version` 因此失败并记为 `L2_RESULT=skip`（CI 设计为非阻塞，
  见 `reports/test-report.md` §2.4）；`test_package` 在 `env="conanrun"` 下同一命令 rc=0。
- 上游 CLI 三个子命令需要真实 iOS 设备，CI 环境无法覆盖功能面，只能覆盖加载/版本/帮助。
- 本包同时产出 CLI，软件级 `commands.json` 已声明（R38）。
---

**编译结束**: 2026-09-22 02:01
**最终状态**: built
