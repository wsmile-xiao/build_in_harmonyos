# itsy_bitsy 0.8 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-03
- 编译器: clang/clang++（OHOS clang 15.0.4，aarch64-unknown-linux-ohos）
- 状态: built（待合并后的 release upload 后才可标记 published）

## 编译步骤

1. 依赖预检（W0/R35/R36）：`bash ci/scripts/preflight_check.sh itsy_bitsy/0.8` →
   唯一 Conan 依赖 `span-lite/0.11.0` 已在制品仓 ohpcd 发布（`conan download --only-recipe` 实测），
   `itsy_bitsy/0.8` 版本号未被占用（R37）。
2. 语言预检（R47）：`ohc-run.py lang-preflight itsy_bitsy 0.8` → detected=cpp（源文件 125 个，cpp 116）。
3. 源码：`https://github.com/ThePhD/itsy_bitsy/archive/refs/tags/v0.8.tar.gz`，SHA256
   `ba76a9b22f41802ede0d7b141f6cf0bf48fa27a88a7181eef8928d6c20ee771d`。Conan 实测三条 URL 校验通过
   （主源码 + range-v3 0.12.0 + span-lite v0.11.0，日志行 "Sources correctly downloaded from …"）。
4. Conan `source()` 将上游空的 `vendor/range-v3`、`vendor/span-lite` 子模块目录补为固定官方源码；
   range-v3 仅用于上游测试，span-lite 同时是 C++17 消费者所需的公共 Conan 依赖。
5. `generate()` 用 `CMAKE_SYSTEM_NAME=Linux` 进入上游兼容的 Unix 分支（OHOS clang 工具链不变），
   开启 single header、upstream tests 与 examples，并设 `CMAKE_CTEST_ARGUMENTS=--output-on-failure`。
6. `build()` 执行补丁 → `cmake --build --parallel 2 -- -j2` → `cmake --build --target test -- -j2`
   （即串行 `ctest --output-on-failure`）。设备构建统一按工作区规则使用 **`-j2`**（不使用 -j4）。
7. 采信命令（与 CI `ci/conan/build_and_test.sh` 逐字同源）：
   `conan create archives/i/itsy_bitsy/0.8 -pr:h=<abs>/ci/conan/profiles/ohos-aarch64 -pr:b=<abs>/… --build=missing --build='itsy_bitsy/*'`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 不认识 HarmonyOS 平台名 | CMake 无 Platform/HarmonyOS 模块，上游 Unix 分支不可用 | toolchain 设 `CMAKE_SYSTEM_NAME=Linux`，编译器仍为 OHOS clang++（E092 已知处理） |
| 2 | 上游测试在 `include/itsy/detail/bit_detail.hpp` 触发 `allocator::construct<char16_t/char32_t>` 的 `-Wdeprecated-declarations` | OHOS libc++ 在 C++17 标记该接口 deprecated，上游测试目标又用 `-Werror` | 仅加 `-Wno-deprecated-declarations`；不改测试与断言 |
| 3 | `include/itsy/tests/shared_allocator_tests.hpp:118` 的 `index` 触发 `-Wunused-but-set-variable` 并在 `-Werror` 下变硬错误 | 上游测试目标追加 `-Wall -Wextra -Werror`，该变量仅递增未使用 | 仅加 `-Wno-error=unused-but-set-variable`（保留警告可见：本轮设备日志中该 warning 仍原样打印，只是不再致命） |
| 4 | 安装后的 `itsy.bitsy-config.cmake` 引用 `sol2-targets.cmake` 与 `sol2` 目标 | 上游配置文件复制残留 | 窄补丁改为加载 `itsy.bitsy-targets.cmake`，导出 `itsy::bitsy` 与 single 目标 |
| 5 | 首次设备构建直接失败：`ERROR: There are invalid packages: span-lite/0.11.0: Invalid: 'settings.os.version' value not defined` | 以相对路径 `-pr:h=ci/conan/profiles/ohos-aarch64` 调用时，Conan 命中本机残留副本 `~/.conan2/profiles/ci/conan/profiles/ohos-aarch64`（缺 `os.version`/`compiler_executables`，且 cppstd=gnu14、libstdc++11） | 改用绝对 profile 文件路径（与 CI 的 `PROFILE_FILE="$REPO_ROOT/ci/conan/profiles/$PROFILE"` 完全一致）。本机共享 profile 属他人环境，未修改 |
| 6 | `CMAKE_CTEST_ARGUMENTS` 传 Python tuple 时 `make test` 规则变成 `ctest ['--output-on-failure']`，ctest 会把字面量 `['--output-on-failure']` 当参数 | Conan 把非字符串 cache variable 序列化为 Python repr，CMake 期望字符串（分号列表） | 改为字符串 `tc.cache_variables["CMAKE_CTEST_ARGUMENTS"] = "--output-on-failure"`；复核生成的 `Makefile:71` 为 `ctest --output-on-failure $(ARGS)`。刻意不用 `CMake.ctest()`：它会注入 `--parallel <tools.build:jobs>`（本机 20），超出工作区并发预算 |
| 7 | 消费者 test_package 无法证明声明的公共依赖真的必需 | `bit_vector`/`popcount` 路径不经过 `itsy/detail/span.hpp` | 新增 `bit_span` 用例走 `itsy/bit_span.hpp → nonstd/span.hpp`；并以移除 span-lite 头路径的负对照证明缺依赖时编译即失败 |
| 8 | **远端 CI 第 1 轮红（构建 #37778，PR e5412936）**：`make` 在 1% 就 `Error 2`，日志首条真实错误是 `single/single.py:138` 的 `os.popen('git describe --tags --abbrev=0').read()` 抛 `TypeError: can't concat str to bytes`（帧 `File "<frozen codecs>", line 321, in decode`，即 `BufferedIncrementalDecoder.decode` 里的 `self.buffer + input`） | 上游 single header 生成脚本在 build 阶段 shell out `git`，并用**解释器从宿主 locale 推导的文本编码**去解码那条管道；CI worker 上该编码是 str-buffered 的（idna/punycode 一族），于是空 stdout 也走进 `str + bytes` 拼接并抛错。设备端复测 `locale.getpreferredencoding(False)` 在 `LC_ALL=C / C.ascii / C.punycode / C.idna / en_US.ISO-8859-1` 下恒为 `UTF-8`，`os.popen(...).read()` 干净返回 `''` → 同一份代码本地全绿、只有 CI 红，属宿主 locale 差异掩盖 | 在 `generate()` 用 Conan `Environment` 给 build 作用域硬 pin `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8`，使 build 阶段所有子 python（含 make 派生的 `single.py`）不再依赖宿主 locale。不改上游源码、不加平台条件宏、不跳测试、不动共享配置。设备端复核：source `build/Release/generators/conanbuild.sh` 后得到 `PYTHONUTF8=1 / PYTHONIOENCODING=utf-8 / preferred=utf-8`，重跑 `conan create` 与上游 CTest 全绿 |
| 9 | **远端 CI 第 2 轮红（构建 #37817，PR d5cb947a0a）**：即使注入 UTF-8 环境，CI worker 仍在 `single/single.py:138` 抛同一 `TypeError`，说明环境变量不足以跨过该运行时的 `os.popen()` 解码路径 | `os.popen().read()` 依赖解释器/宿主 codec，无法保证 HarmonyOS worker 行为一致 | 新增 `0002-single_version_popen_bytes.patch`，用 `subprocess` 捕获原始 bytes、以 UTF-8 replacement 解码，并在 git 探测异常时返回空字符串，保留上游 `Tip` fallback；不改变生成头文件内容语义 |


### 问题 #8 的本地复现与修复反证（不必等 CI）

设备默认 `locale.getpreferredencoding(False)` 恒为 UTF-8，正常跑永远复现不到；用强制
str-buffered codec 模拟 CI worker 的编码解析结果：

```text
$ PYTHONIOENCODING=idna python3 single/single.py --input <include> --output a.hpp b.hpp
exit=1，崩在同一条增量解码路径（与 CI 的 "can't concat str to bytes" 同族）：
    object type name: UnicodeError
    object repr     : UnicodeError('label empty or too long')
    lost sys.stderr

$ env PYTHONIOENCODING=idna PYTHONUTF8=0 sh -c ". <配方生成的>conanbuild.sh && python3 single/single.py ..."
exit=0    Current version: Tip (revision )        ← 配方的 buildenv pin 覆盖了宿主继承的坏编码
```

即：单靠"CI 环境不同"解释不算修好；这里给出了同一条代码路径在坏编码下必崩、
在配方注入的编码下必过的双向证据。

## 源码修改

`patches/0001-cmake-itsy.bitsy-config.cmake.in.patch`：修复上游安装 CMake 配置的复制残留，使
`find_package(itsy.bitsy CONFIG REQUIRED)` 能加载实际导出目标并提供 `itsy::bitsy` / `itsy::bitsy::single`。
补丁完整性已在设备端复核：把该补丁应用到未修改的 `cmake/itsy.bitsy-config.cmake.in` 后，与本次构建实际使用的文件
`cmp` 逐字节一致；未修改任何上游测试源文件、断言或 `WILL_FAIL` 语义；补丁不含任何平台条件编译宏。

`patches/0002-single_version_popen_bytes.patch`：修复 HarmonyOS worker 上上游 `single/single.py` 的
`os.popen().read()` codec 不兼容问题。改为捕获 bytes 后防御性解码，git 不可用/非仓库时返回空值，继续使用上游 `Tip` 版本回退。

## 依赖版本

| 用途 | 版本 |
|------|------|
| OHOS Kernel | HongMeng Kernel 1.12.0 aarch64 |
| Python | 3.12.8 |
| Conan | 2.29.1 |
| CMake | 4.1.2 |
| Clang | 15.0.4 (aarch64-unknown-linux-ohos) |
| span-lite（公共依赖 + 上游测试源码） | 0.11.0 |
| range-v3（仅上游测试源码） | 0.12.0 |

## 验证结果

采信构建：`conan create`（-j2）退出码 0，日志
`$HOME/tmp/itsy_bitsy-0.8-owner/logs/conan-create-j2.log`，构建目录 `~/.conan2/p/b/itsy_365bd417b49e0`。

提交后另用 CI 同源脚本复跑一遍（`zsh ci/conan/setup.sh` + `zsh ci/conan/build_and_test.sh archives/i/itsy_bitsy/0.8`，
`CI_BRANCH=feat/itsy_bitsy-0.8`），`BUILD_RC=0`，日志
`$HOME/tmp/itsy_bitsy-0.8-owner/logs/w3-post-commit.log`：

```text
G0_RESULT=pass      G0e: Root directory whitelist passed
L0_RESULT=pass: all checks passed      （L0i 依赖已发布 / L0j 版本未占用 / L0k 库类型无需 commands.json /
                                        L0n 分支名 feat/itsy_bitsy-0.8 匹配 itsy_bitsy-0.8）
KC_RESULT=pass      JC_RESULT=pass     （知识库质量、杂项文件门禁）
100% tests passed, 0 tests failed out of 20     ← CTest（含 examples）
  其中上游 tests/ 正式入口 6/6，独立 examples 检查 14/14；PR 统计按正式入口计 6
100% tests passed, 0 tests failed out of 5      ← test_package 消费者
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: no bin/ dir                     ← header-only，无命令行程序
L4_RESULT=warn: dangerous functions in patches  ← 误报，见下方"L4 误报"
L5_RESULT=pass: lib/ has content
[sabotage] lib/ moved away / [sabotage] include/ moved away
L1e_RESULT=pass: Negative test confirmed — test genuinely depends on itsy_bitsy
```

**L4 误报说明**（不修代码，登记依据）：CI 的 L4 用 `grep -rlE '(strcpy|sprintf|gets|strcat)\b'` 扫补丁，
命中的是本仓库根本改不动的文件名 `itsy.bitsy-tar`**`gets`**`.cmake` 里的子串 `gets`（唯一两处命中即补丁第
14/15 行的该文件名），并非真实危险函数调用；补丁未引入任何 `strcpy/sprintf/gets/strcat` 调用。

**CI 同源脚本的 conandata 副作用**（已复核未污染提交）：脚本的 mirror fallback 会把 `conandata.yml` 的
`url:` 改写成 `gh-proxy.com` 列表，而 `file://` 预下载还原钩子只回滚预下载那一步，改写会残留在工作树。
运行后 `git status --short` 确实显示 ` M archives/i/itsy_bitsy/0.8/conandata.yml`；已把改写版本另存为
`$HOME/tmp/itsy_bitsy-0.8-owner/conandata.mirror-rewrite-evidence.yml` 作为证据，并把工作树恢复成提交里的
官方单条 URL（`.gitcode/review-memory.md` §13 明确 CI 自己加镜像，PR 里只写官方原始 URL）。

```text
上游 tests/ 正式 CTest          100% tests passed, 0 failed out of 6    (Total Test time 3.94 s)
examples（独立可选检查）         14/14 通过；启用 examples 时完整 CTest 为 20/20
  itsy.bitsy.tests.run_time            Passed 0.47 s
  itsy.bitsy.tests.run_time.single     Passed 0.39 s
  itsy_bitsy.tests.compilation[.single] Passed ×2
  itsy_bitsy.tests.fail.*              Passed ×2（上游 WILL_FAIL 负向编译检查）
  itsy.bitsy.example.*                 Passed ×14
上游 Catch2 逻辑用例（两个驱动分别直跑，--reporter compact，退出码均 0）
  Passed all 554 test cases with 3640828 assertions.   （×2 → 1108 次逻辑用例，7281656 条断言）
Conan test_package（安装后消费者，find_package(itsy.bitsy) + itsy::bitsy + nonstd::span-lite）
  100% tests passed, 0 tests failed out of 5
  1/5 binary_digits / 2/5 bit_vector / 3/5 bit_vector_flip / 4/5 popcount / 5/5 bit_span  全部 Passed
  直跑 "./test_itsy_bitsy bit_span" → PASS: bit_span（退出码 0）
```

### 断言可失败性取证（每条都真的能失败）

消费者测试共 5 个 CTest 用例、27 条运行期断言 + 1 条 `static_assert`。逐条把期望值改错后跑
`conan test`，全部产生真实失败；随后复原并整轮通过（源文件 sha256 复原前后一致：
`97e0d319573fc3a215ddbe1c228aac2ebc0343c85c032bf251b2cf63f5010a43`）。
证据目录 `$HOME/tmp/itsy_bitsy-0.8-owner/mutations/`（含每次运行的完整日志与 `summary.txt`）。

| # | 破坏点 | `conan test` 退出码 | 第一条真实失败 |
|---|--------|--------------------|----------------|
| M0 | 负对照：编译消费者源码时移除 span-lite 头路径 | clang 1 | `include/itsy/detail/span.hpp:47:2: error: "Cannot use this feature: a span of some sort is required!…"` |
| M1 | `static_assert(binary_digits_v<unsigned char> == 8` → `== 9` | 1 | `test_itsy_bitsy.cpp:18:1: error: static assertion failed due to requirement 'bitsy::binary_digits_v<unsigned char> == 9'` |
| M2 | `binary_digits_v<unsigned short> == 16` → `== 15` | 1 | `FAIL: bitsy::binary_digits_v<unsigned short> == 15 (line 44)` → `1 - binary_digits (Failed)` |
| M3 | `bit_vector` 置位后 `count(true) == 2` → `== 3` | 1 | `FAIL: bits.count(true) == 3 (line 57)` → `2 - bit_vector (Failed)` |
| M4 | `flip` 后 `count(true) == 0` → `== 1` | 1 | `FAIL: bits.count(true) == 1 (line 72)` → `3 - bit_vector_flip (Failed)` |
| M5 | `popcount(0xF0) == 4` → `== 5` | 1 | `FAIL: bitsy::popcount(static_cast<unsigned char>(0xF0)) == 5 (line 84)` → `4 - popcount (Failed)` |
| M6 | `bit_span` 写回底层字节 `storage[1] == 0x80` → `== 0x08` | 1 | `FAIL: storage[1] == 0x08 (line 105)` → `5 - bit_span (Failed)` |
| 控制组 | 全部复原后重跑 | 0 | `100% tests passed, 0 tests failed out of 5` |

消费者侧 `test()` 也统一到 -j2 预算：`cmake --build … --target test -- -j20 -j2`（末次 -j 生效），
5/5 通过 + 直跑 `./test_itsy_bitsy bit_span` → `PASS: bit_span`；日志
`$HOME/tmp/itsy_bitsy-0.8-owner/logs/consumer-control-j2test.log`。

### W4 Pre-PR 独立审计

`scripts/pre_pr_audit.py generate` + 上下文隔离的独立审计子任务（规则：`.gitcode/code-style.md`、
`.gitcode/review-memory.md`、`templates/audit-prompt.md` 第 0 步阻断性分级表）：
**verdict=pass，P0=0 / P1=0 / P2=2 / P3=4**，报告 `archives/i/itsy_bitsy/0.8/reports/audit-result.json`
（本机证据，按 `.gitignore` 不入库）。审计侧独立 curl 复核了三条官方归档 sha256，并把提交内补丁应用到未修改
v0.8 源码后与设备构建文件逐字节比对。P2/P3 处置：

| 项 | 处置 |
|----|------|
| P2 conandata 被 CI 脚本改写残留 | 采纳：还原为提交内官方单条 URL，改写版另存证据；只显式 add 本任务路径 |
| P2 L4 危险函数 warn | 登记为误报（命中文件名 `itsy.bitsy-targets.cmake` 里的 `gets` 子串），按分级表非阻断 |
| P3 消费者 `cmake.test()` 注入 `-j20` | 采纳：改为 `cmake.test(build_tool_args=["-j2"])` 并复验 5/5 |
| P3 MANIFEST `source:` 路径写成 `itsy_bitsy-v0.8/` | 采纳：`tar tzf` 复核实际根目录为 `itsy_bitsy-0.8/`，已订正 |
| P3 README 代码块内 `\\` 续行 | 采纳：改为单反斜杠，并补 profile 必须绝对路径的说明 |
| P3 `patch_description` 建议改序号式 | 采纳：改为 `.gitcode/code-style.md` §12 的"序号 + 空格词组"形式 `0001 cmake itsy.bitsy-config.cmake.in load itsy.bitsy targets`，同时保留可读语义 |

上游侧不做“人为破坏断言”（上游 Catch2 自带失败语义，且本任务禁止修改上游测试）；
其可信度由上游 tests/ 的 6/6 CTest 直跑、另有 examples 14/14 通过、两个驱动的 `554 / 3640828` 汇总行，以及 `--output-on-failure`
输出通道共同保证。

## 注意事项

- 这是 header-only 包：`include/`、`lib/cmake/`、`share/pkgconfig/`、`licenses/`，无 `bin/`，
  因此 `commands.json` 不适用（CI L0k 对库类型不要求），L2 smoke test 自然跳过。
- `status: built` 不表示已上传 release 制品；正式 `published` 以合并后的 release upload 为准。
- 归档目录内的构建产物（`test_package/build/`）、`reports/`、`*.log`、`.ci-result.json`、
  `ci-metadata.json`、`CMakeUserPresets.json` 均为工具生成的本机证据，按 `.gitignore` 与
  `.gitcode/review-memory.md` §19 不进入提交。
- 上游测试通过，无豁免项；未使用放宽权限、写系统目录、全局 `LD_LIBRARY_PATH`、空实现或静态链接。
