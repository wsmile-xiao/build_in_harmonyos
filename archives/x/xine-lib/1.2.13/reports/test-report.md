# 测试报告 — xine-lib 1.2.13（HarmonyOS PC）

- 软件：xine-lib 1.2.13（库 libxine；上游工程 xine，SourceForge）
- 构建系统：autotools（configure + make）
- 目标平台：OpenHarmony PC / aarch64（`aarch64-unknown-linux-ohos`，musl libc，clang 15）
- 构建方式：真实 `conan create`（profile `ci/conan/profiles/ohos-aarch64`），6 个适配补丁全部应用
- 证据根目录：`<worktree>/.ohc-logs/`、`archives/x/xine-lib/1.2.13/reports/conan-create.log`

## 1. 上游自动化测试套件：**不存在**

| 检查项 | 命令 | 原始输出/退出码 |
|---|---|---|
| `make check` | `make check`（全部子目录） | 每个子目录均 `Nothing to be done for 'check'.`；`rc=0`。日志：`.ohc-logs/make-check-1.log` |
| 测试注册 | `grep -rnE "TESTS *=|check_PROGRAMS" --include=Makefile.am .` | 无匹配（`rc=1`）。日志：`.ohc-logs/upstream-test-entries.log` |
| CTest / CMake 测试 | `grep -rnE "enable_testing|add_test|BUILD_TESTING|ctest" .` | 无匹配 |
| pytest / unittest / cargo / go test | `grep -rnE "pytest|unittest|cargo test|go test" .` | 无匹配 |
| 测试目录 | `find . -type d \( -iname "test*" -o -iname "check" \)` | 无 |

**结论：上游没有自动化测试套件，没有 `make check` 目标。** 因此本报告以"上游真实测试/样例入口"的实测统计为准（下节），`test_package/` 统计单独列示，不替代上游统计。

## 2. 上游真实测试/样例入口清点与实测（程序级入口 7 个；含不适用说明）

> **计数口径与 `test_package/MANIFEST.yml` 的 `upstream_tests` 完全一致（同为 7 个条目）**：
> 上游入口（程序级）= **7** = 实测程序 **3** + 不适用入口 **2** + 库内编译单元 **2**；
> 其中 3 个实测程序共调用 **6** 次，全部通过（PASS 6 / FAIL 0 / SKIP 0）。

| # | 入口（程序 / 编译单元） | 类型 | 实际执行命令 | 调用次数 | 结果 | 日志路径 |
|---|---|---|---|---|---|---|
| 1 | `xmltest`（src/xine-utils） | `noinst_PROGRAMS`（上游唯一带测试语义的入口，`-DXINE_XML_PARSER_TEST`） | `./src/xine-utils/xmltest <xml>` | 2（正常 XML / 畸形 XML） | **PASS** `rc=0` ×2 | `.ohc-logs/upstream-sample-xmltest-ok.log`、`…-bad.log` |
| 2 | `xine-list`（misc） | `bin_PROGRAMS` | `./misc/xine-list-1.2 --help`；`XINE_PLUGIN_PATH=<plugins> ./misc/xine-list-1.2 -a` | 2 | **PASS** `rc=0` ×2（`-a` 枚举全部支持格式，插件加载正常） | `.ohc-logs/upstream-sample-xinelist-help.log`、`…-all.log` |
| 3 | `cdda_server`（misc） | `EXTRA_PROGRAMS` | `./misc/cdda_server`；`./misc/cdda_server /dev/null 9999` | 2 | **PASS**（无参 usage `rc=255`；带参启动监听被 `timeout` 终止 `rc=124` 属预期） | `.ohc-logs/upstream-sample-cdda.log`、`…-cdda2.log` |
| 4 | `xine-fontconv`（misc） | `EXTRA_PROGRAMS` | `make -C misc xine-fontconv` | 0 | **不适用**：`fatal error: 'ft2build.h' file not found`（freetype2 为可选依赖，configure 默认未启用） | `.ohc-logs/upstream-misc-programs-build.log` |
| 5 | `contrib/libdha/kernelhelper/test.c` | `EXTRA_PROGRAMS` | `make -C contrib/libdha test` | 0 | **不适用**：`error: call to undeclared function 'iopl'`（x86 端口 I/O；aarch64/OHOS 无该接口，DGA 亦不适用） | 见"不适用说明" |
| 6 | `input_test.c`（src/input） | 库内编译单元（builtin 插件 `xineplug_inp_test.la`） | 随 `make` 编入 libxine（`in_builtins`） | 0 | **已编入 `libxine.so`**，由 `xine-list` 加载验证 | `.ohc-logs/make-3.log` |
| 7 | `sound_tester.c`（src/post/goom） | 库内编译单元 | 随 goom post 插件编译 | 0 | **`sound_tester.lo` 生成** | `.ohc-logs/make-3.log` |

### 统计（上游入口）

| 项 | 数量 |
|---|---|
| 上游自动化测试套件 | 0 |
| **上游入口（程序级，清点）** | **7** |
| 实测程序 | 3（`xmltest` / `xine-list` / `cdda_server`） |
| 实测用例调用（执行次数） | 6 |
| 通过 | 6 |
| 失败 | 0 |
| 跳过 | 0 |
| 不适用（平台/可选依赖） | 2 |
| 库内编译单元（无独立运行入口，随库编译验证） | 2 |

### 不适用说明

- **#4 `xine-fontconv`**：`EXTRA_PROGRAMS`，默认不随 `make` 构建；其构建硬依赖 freetype2（`ft2build.h`）。xine-lib 的 freetype 支持是可选特性（`configure.ac:315`，默认 `no`），本次 OHOS 配置未启用，因此该工具不适用。日志：`.ohc-logs/upstream-misc-programs-build.log`。
- **#5 `contrib/libdha/test`**：libdha 是 x86/X11 DGA 专用组件，`sysdep/pci_linux.c` 调用 `iopl()`（x86 端口 I/O 权限）。aarch64/OHOS 无该接口，且 DGA 在 OHOS 上无意义，故不适用。

## 3. test_package（消费者视角，**不替代**上游统计）

- 用例：`test_package/test.c`（`conan create` 内由 CMake 构建并运行）
- 断言总数：**8**
- 通过：**8**，失败：0，跳过：0
- 其中**鸿蒙特有用例 2 条**：
  1. `OHOS: toolchain defines __OHOS__ (native aarch64-linux-ohos build)`
  2. `OHOS: glibc headers are not in use (musl libc expected)`
- 其余 6 条为 libxine 公共 API 消费者断言：`xine_new()` / `xine_get_version_string()`（含 1.2.x 系列校验）/ `xine_get_version()==1.2.13` / `xine_check_version(1,2,13)==1` / `xine_exit()`

原始输出（`conan create` 日志）：

```
PASS: OHOS: toolchain defines __OHOS__ (native aarch64-linux-ohos build)
PASS: OHOS: glibc headers are not in use (musl libc expected)
PASS: xine_new() returns an engine handle
PASS: xine_get_version_string() returns a string
PASS: linked libxine reports the 1.2.x series
PASS: xine_get_version() reports 1.2.13
PASS: xine_check_version(1,2,13) reports an ABI-compatible library
PASS: xine_exit() releases the engine without crashing

8/8 assertions passed, 0 failed
```

证据：`archives/x/xine-lib/1.2.13/reports/conan-create.log`（第 4439–4449 行）。

## 4. 上游测试在构建中的集成

`conanfile.py` 的 `build()` 在 `make` 之后自动运行上游 `xmltest`（R51 三步法第 2 步）：

```
xine-lib/1.2.13@ohpcd/stable: RUN: ./src/xine-utils/xmltest ".../xmltest-sample.xml" > xmltest.out 2>&1
```

证据：`reports/conan-create.log`（第 1121–1127 行构建 `xmltest`，第 3655 行运行）。

## 5. 结论

- 上游无自动化测试套件（如实声明，附清点证据：`make check` 25 处空转 + 四类框架探针全无命中）。
- 上游入口（程序级）共 **7** 个，与 `test_package/MANIFEST.yml` 的 `upstream_tests` 条目数一致：3 个实测程序（6 次调用全通过）、2 项因平台/可选依赖不适用、2 项为库内编译单元。
- 消费者 `test_package` 8/8 通过，其中鸿蒙特有断言 2 条（≥1 满足）。
- 未发现漏测的上游样例入口。
