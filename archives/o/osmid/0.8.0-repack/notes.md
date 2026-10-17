# osmid 0.8.0-repack 适配笔记

## 编译环境

- 构建系统: cmake（顶层 CMakeLists.txt，目标 m2o、o2m）
- 编译日期: 2026-10-10
- 编译器: clang/clang++（HarmonyOS PC aarch64，conan profile 提供）
- 状态: built（首轮工作树，真机 rule4 门禁待验证）
- 申请人: gcw_uQ09W7jl，队伍名称：干

## 版本口径

- 任务版本 `0.8.0-repack` = Debian `0.8.0~repack` 的平台归一化（`~` → `-`，与 leaflet-markercluster `1.5.3-dfsg` 先例一致）。
- 上游对应 GitHub tag `v0.8.0`（commit 2a5c8eb），源码取官方发布包 `osmid-0.8.0.tar.gz`（1127417 字节，sha256 见 conandata.yml）。
- Debian repack 仅为打包调整，上游代码即 v0.8.0；配方不使用 Debian 池 tarball（直连不可达），以官方 GitHub 源为准，CI 自动追加 gh-proxy 镜像 fallback。

## 编译步骤

1. `get()` 解包官方 v0.8.0（strip_root）。
2. `apply_conandata_patches()` 打 `0001-cmake-ohos-alsa-x11.patch`。
3. `CMakeToolchain` 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 `cmake_minimum_required(VERSION 3.0)`，CMake≥4 必需，oscpack 先例）；OHOS 下另注入 `OSMID_OHOS=ON`（X11 取舍开关；Linux 原生构建不注入），并将 `alsa-lib/1.2.16` 的 `include`/`libasound.so` 转发给 `FindALSA`（`ALSA_INCLUDE_DIR`/`ALSA_LIBRARY` cache 变量）。OHOS 编译器由 `_resolve_ohos_compilers()` 在 generate() 期动态定位（profile 路径缺失时回退 PATH/OHOS-SDK 候选并做 `--version` 存活校验），随后写入 `CMAKE_C/CXX_COMPILER` 并直接改写已生成的 toolchain 文件，平台身份保持 conan 原生 HarmonyOS（不伪装 Linux）。
4. `cmake.configure()` + `cmake.build()` 构建 m2o、o2m（内嵌 JUCE + oscpack_1_1_0 + spdlog-0.11.0 + cxxopts，无需外部 oscpack/fmt）。
5. `cmake.install()` 安装 `bin/m2o`、`bin/o2m`（上游 UNIX 分支已有 install 规则）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `target_link_libraries(... X11)` 在 OHOS 无 X 环境 | 两个工具为无头 MIDI 桥，仅用 juce_audio_* + juce_core + juce_events（无 GUI 模块），X11 链接非必需 | 补丁以内层 `if(OSMID_OHOS)` 在鸿蒙下去掉 X11（`OSMID_OHOS` 由配方仅在 settings.os==OHOS 时注入，显式开关而非平台名判断）；Linux 保持原样；补丁不引入 `__OHOS__` 宏（PF5 门禁） |
| 2 | `find_package(ALSA REQUIRED)` 在干净 OHOS 环境找不到系统 ALSA | OHOS 无 `/usr/include/alsa`，ALSA 由 `alsa-lib/1.2.16` 制品提供 | `generate()` 从 `self.dependencies["alsa-lib"]` 取 `package_folder` 并写入 cache 变量；`requirements()` 仅声明 `alsa-lib/1.2.16`（已发布，zita/aeolus 先例） |
| 3 | `cmake_minimum_required(VERSION 3.0)` 在新 CMake 下配置失败 | CMake≥4 删除对 <3.5 的兼容 | `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"]="3.5"`（oscpack 先例，必须是 cache 变量） |
| 4 | `m2o/o2m --version` 会进入 MIDI 打开 + 心跳循环而挂起 | `--version` 分支打印后返回 0，主函数继续走设备打开与 `while(!g_wantToExit)` | 测试一律用 `--help`（返回 1 即退）与未知选项（返回非零），不用 `--version` 做断言 |
| 5 | 真机 `cmake.configure()` 在 `CMakeLists.txt:1 (project)` 报 `CMAKE_C/CXX_COMPILER` 错误，伴随 `System is unknown to cmake, create: Platform/HarmonyOS` | CMake 无 HarmonyOS 平台模块，project() 处编译器自检默认链接可执行文件做探测 | `generate()` 注入 cache 变量 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`（只改探测形态，不伪装平台、不跳过测试；最终 m2o/o2m 仍完整链接） |
| 6 | 上游顶层 `project(osmid)` 写在 `cmake_minimum_required(VERSION 3.0)` 之前 | CMake 要求 minimum 先行，CMake≥4 下顺序错误叠加未知平台会放大配置失败 | 补丁首 hunk 仅交换这两行顺序（不改版本号，兼容逻辑仍靠 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 注入） |
| 7 | 同一编译器自检失败连续 3 轮：`STATIC_LIBRARY` + `COMPILER_WORKS` 掩饰均未起效，C/CXX 双双在 `project()` 处失败 | 前三轮均假设卡在链接/自检子步段，但未知平台下整个探测路径未配置（`System is unknown to cmake` 后平台变量留空），掩饰不可能生效；真机摘要截掉 clang 真实报错 | 第 2 策略周期换路线：不再掩饰自检，修复平台身份本身——OHOS 下映射 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（oystr/observer-ptr-lite/open-scene-graph E092 合入先例），使平台模块解析、`IF(UNIX)` 走对、真实 try-compile 链接照常跑；X11 取舍改用 `OSMID_OHOS` 显式开关（映射后 SYSTEM_NAME 无法区分 OHOS/真 Linux）；保留双通道诊断转储 |
| 8 | 第 2 周期 Linux 映射仍失败：`project()` 处 C/CXX identification unknown，`conan_toolchain.cmake` 疑仍为 HarmonyOS | 上一方案经 `tc.cache_variables["CMAKE_SYSTEM_NAME"]` 注入，但 conan CMakeToolchain 已按 settings.os==OHOS 生成自己的 `set(CMAKE_SYSTEM_NAME HarmonyOS CACHE...)` 块；二次 CACHE set 无 FORCE 时首写获胜，覆盖被静默忽略，未知平台身份实际未变；旧诊断只转储注释行 + 固定单路径 CMakeError.log（CMake4 scratch 布局下找不到文件），真因仍被摘要截断 | 第 4 策略周期换实现路线：改用原生 `tc.system_name="Linux"` + `tc.system_processor="aarch64"`（conan Toolchain system API，在源头块覆盖而非事后 CACHE 竞争；配 cache 双保险兼容无该属性的老 conan）；去掉 STATIC/COMPILER_WORKS 掩饰；诊断升级为编译器活体探针（`--version` + hello.c 试编，排查 lld 缺 libxml2 等 wrapper 故障）+ 全候选 CMakeError/Output.log 递归搜索 + HMBS_EVIDENCE 前缀防摘要过滤 |
| 9 | 第 4 周期活体探针给出直接证据：`/data/service/hnp/bin/clang{,++} --version` 均报 `[Errno 2] No such file or directory`，前两周期的平台身份/自检形态假设全错 | profile 的 `tools.build:compiler_executables` 硬编码路径在预检 worker 上根本不存在，二进制缺失导致任何 `project()` 探测必然报 identification unknown；与 SYSTEM_NAME 无关 | 第 5 策略周期换路线：放弃 Linux 伪装（亦避开 DRAFT-nng PF5/W4 平台伪装旗标，保持 conan 原生 HarmonyOS 身份），改为 generate() 期编译器动态发现（profile conf 优先、存活校验 `--version` rc==0；回退 `shutil.which(clang/clang++)`、CC/CXX 环境、`/storage/.../usr/local/bin` 与 OHOS-SDK llvm 候选；无可用时明错中断）+ `CMAKE_C/CXX_COMPILER` cache 注入 + 直接改写已生成 toolchain 文件防 CACHE 竞争；诊断保留 HMBS_EVIDENCE 双通道 |
| 10 | 第 5 周期发现可用编译器却未生效：resolve 选出 `.harmonybrew/bin/clang{,++}`，但工具链仍为 `/data/service/hnp/bin/clang` 且诊断仍探死路径 | `_patch_toolchain_compilers` 只替换 conf 取到的 stale 字符串，而预检证明 worker 上 conf 为 None，改写零替换；`_dump` 又用带死路径默认值的 conf 回退，证据失真 | 第 6 策略周期改实现：改写逻辑改为无条件替换已知死路径（CXX/++ 优先防子串污染，计替换数并在零替换时告警），`_resolve` 候选补入 harmonybrew 实测路径，`_dump` 优先复用 resolve 结果使证据与 generate() 选择一致 |
| 11 | 真机 2026-10-10 预检：编译器已解决（toolchain 改写 2 replacements 生效，cmake.configure 通过），`m2o.cpp` 编译内嵌 `spdlog-0.11.0/details/os.h:354` 报 `no matching conversion from 'int' to 'std::string'`（`std::string(strerror_r(...))`） | 内嵌 spdlog-0.11.0 的 `errno_str` 按 `#elif FreeBSD/APPLE/ANDROID/(POSIX&&!_GNU_SOURCE)` 二分：GNU 分支假设 `strerror_r` 返回 `char*`；musl（HarmonyOS/OHOS）只提供 XSI 版（返回 int、消息写 buf），预检机走 GNU 分支即类型错。与前 6 周期的编译器定位/平台身份问题无关，是新失败域（证据：configure 已过、make 到 m2o 才挂） | 首轮尝试新增 `0002-spdlog-musl-strerror-r.patch`（`#elif` 追加 `!defined(__GLIBC__)`），但 2026-10-10 预检在 `apply_conandata_patches` 即失败（`source file is different`），补丁未生效；诊断不变，转见 #12 换路线 |
| 12 | #11 的 `.patch` 文件在真机 `apply_conandata_patches` 报 `source file is different`（`WARN: ... 0002-spdlog-musl-strerror-r.patch: actual: b'#elif defined(__FreeBSD__) ...'`），构建未进入编译即中断 | `.patch` 走 conan 内置 applier，对 hunk 头/行尾严格，跨平台易碎；且同一指纹第 2 次修复不得原样重复 | 删除 `0002` 补丁文件及其 conandata 注册，改用 `build()` 内 `_patch_spdlog_musl()` 行锚定文本改写（锚点 `defined(ANDROID) \|\| \` 恰出现 1 次才替换为 `defined(ANDROID) \|\| !defined(__GLIBC__) \|\| \`，否则抛 `ConanException` 中断；已存在标记则跳过），`apply_conandata_patches` 之后、`cmake.configure` 之前执行；glibc+`_GNU_SOURCE` 仍走 GNU 分支，无 `__OHOS__` 宏，不改测试口径 |
| 13 | 2026-10-10 预检：spdlog 修法生效（构建越过 `m2o.cpp`，新挂点为 `JuceLibraryCode/include_juce_audio_devices.cpp` 经 `juce_audio_devices.cpp:131` 报 `fatal error: 'alsa/asoundlib.h' file not found`）；失败命令行的 `-I` 含 oscpack/spdlog/JUCE/cxxopts，唯独无 ALSA 头目录 | 上游 `CMakeLists.txt` 只 `find_package(ALSA REQUIRED)` + 链接 `${ALSA_LIBRARY}`，全局 `include_directories` 仅覆盖 oscpack/spdlog/JUCE/cxxopts、从未加入 `${ALSA_INCLUDE_DIRS}`；桌面 Linux 仅因 `/usr/include` 隐式可用而通过，OHOS worker 的 ALSA 头只在 conan 包目录。前两轮的 spdlog 策略已证实有效（挂点推进），本轮是新失败域 | 换路线：不动源码，`generate()` 内以 `tc.extra_cflags/extra_cxxflags` 追加 `-I<alsa-lib包include>`（与 `ALSA_INCLUDE_DIR` 同源），经工具链全局生效；`find_package(ALSA)` 缓存转发保持不变 |
| 14 | 2026-10-10 预检：ALSA 修法生效（configure 通过、构建越过音频设备文件，新挂点为 `JuceLibraryCode/include_juce_core.cpp` 经 `juce_posix_SharedCode.h:992/1364` 报 `use of undeclared identifier 'pthread_cancel'/'pthread_setcancelstate'`，经 `juce_linux_SystemStats.cpp:132-133` 报 `use of undeclared identifier '_NL_IDENTIFICATION_LANGUAGE'/'_NL_IDENTIFICATION_TERRITORY'`） | 内嵌 JUCE（~2017）假设 glibc：OHOS/musl 头不声明线程取消函数（上游对 Android 已是 `jassertfalse` 无操作先例），且 musl 的 `<langinfo.h>` 无 `_NL_IDENTIFICATION_*` 扩展。与前序编译器定位/spdlog/ALSA 问题无关，是新失败域（证据：configure 已过、挂点逐轮推进） | 换路线但沿用已验证的构建期行锚定改写（`.patch` 在 #12 已证 fragile，不新增补丁文件）：`build()` 内新增 `_patch_juce_musl()`，三处各锚点恰出现 1 次才改写——(a)`pthread_cancel` 调用套 `#if defined(__GLIBC__)`＋`#else jassertfalse`（Android 先例）；(b)`pthread_setcancelstate` 调用套 `#if defined(__GLIBC__)`（不动外层 `#if JUCE_ANDROID` 的 JNI 分支）；(c)两行 `_NL_*` 套 `#ifdef __GLIBC__`，musl 下返回空字符串（无头 MIDI 桥不查询显示语言）。判别一律用 `__GLIBC__`（spdlog 先例），无 `__OHOS__` 宏，glibc/Linux 行为不变；锚点不符抛 `ConanException` 中断 |
| 15 | 真机 2026-10-10 预检：全部编译通过后 `m2o` 链接报数十个 `undefined symbol: snd_*`（`snd_seq_open`、`snd_midi_event_new` 等），链接命令行仅有内嵌 `liboscpack.a`，无 `libasound`、`pthread`、`dl`、`rt` | 上游三处 UNIX 守卫在 conan 原生 HarmonyOS 身份下全为假：CMake 无 HarmonyOS 平台模块，`UNIX` 变量为假，故 `find_package(ALSA)` 未执行、`elseif(UNIX)` 链接块（含 `${ALSA_LIBRARY}`）与 `if(UNIX)` 安装规则整体跳过；`OSMID_OHOS` 内层分支因写在 UNIX 块内部而 unreachable。JUCE 仍经编译器 `__linux__` 宏编译进 ALSA 路径，故表现为编过链不过。与 ALSA 头路径、编译器定位、spdlog/JUCE 文本改写无关，是新失败域（证据：挂点从编译推进到链接，且缺的不只是 asound，还有 pthread/dl/rt） | 换路线：补丁三处守卫放宽为 `UNIX OR OSMID_OHOS`（`find_package(ALSA)`、`elseif` 链接块、`if` 安装规则），内层 `if(OSMID_OHOS)` 去 X11 逻辑不变；`OSMID_OHOS` 仅配方在 settings.os==OHOS 时注入，Linux 行为不变，无 `__OHOS__` 宏；本地用官方 v0.8.0 原始 CMakeLists.txt 重建验证 `git apply --check` 通过，打补丁后三处守卫均含 OSMID_OHOS |

## 源码修改

- `patches/0001-cmake-ohos-alsa-x11.patch`：hunk1 仅交换顶层 `cmake_minimum_required`/`project` 顺序（CMake≥4 要求）；hunk2 放宽 `find_package(ALSA)` 的 `elseif(UNIX)` 为 `UNIX OR OSMID_OHOS`；hunk3 放宽链接块 `elseif(UNIX)` 为 `UNIX OR OSMID_OHOS`（内层 `if(OSMID_OHOS)` 去 X11，配方仅在 settings.os==OHOS 时注入该开关；Linux 原生构建保持 X11）并放宽安装规则 `if(UNIX)` 为 `UNIX OR OSMID_OHOS`（原生 HarmonyOS 身份下 `UNIX` 为假，否则安装规则整体跳过、`cmake --install` 装不出 `bin/m2o`、`bin/o2m`）。无 `__OHOS__` 宏，无生成文件修改。
- `patches/0002-spdlog-musl-strerror-r.patch`：已删除（真机 `apply_conandata_patches` 报 `source file is different`，见 #12）。替代方案为 `conanfile.build()` 内 `_patch_spdlog_musl()` 构建期行锚定改写：内嵌 `spdlog-0.11.0/include/spdlog/details/os.h` 的 `errno_str` 的 `#elif` 行锚点 `defined(ANDROID) || \` 恰出现 1 次时改写为 `defined(ANDROID) || !defined(__GLIBC__) || \`，非 glibc（含 musl/OHOS）走 XSI 分支（`strerror_r` 返回 int，`std::string(buf)`）；glibc+`_GNU_SOURCE` 仍走 GNU 分支。无 `__OHOS__` 宏，无测试口径变化；锚点不符直接抛错中断。
- 内嵌 JUCE musl 守卫（见 #14，无 `.patch` 文件，`conanfile.build()` 内 `_patch_juce_musl()` 构建期行锚定改写，`apply_conandata_patches` 之后、`cmake.configure` 之前执行）：`JuceLibraryCode/modules/juce_core/native/juce_posix_SharedCode.h` 内 `pthread_cancel` 调用套 `#if defined(__GLIBC__)`＋`#else jassertfalse`（Android 无取消支持先例），`pthread_setcancelstate` 调用套 `#if defined(__GLIBC__)`（外层 `#if JUCE_ANDROID` 的 JNI 分支不动）；`juce_linux_SystemStats.cpp` 内两行 `_NL_IDENTIFICATION_*` 套 `#ifdef __GLIBC__`，musl 下 `getUserLanguage/getUserRegion` 返回空字符串。判别一律用 `__GLIBC__`，无 `__OHOS__` 宏，glibc/Linux 行为不变；三处锚点各恰出现 1 次，已用官方 v0.8.0 原始文件核对，不符抛 `ConanException` 中断；已打标记则跳过。

## 依赖版本

- `alsa-lib/1.2.16`（registry 已有，R36 合规；构建期头文件 + 运行期 `libasound.so`）。
- 内嵌第三方（随源码包，不单独声明）：`external_libs/oscpack_1_1_0`、`spdlog-0.11.0`、`cxxopts`、`JuceLibraryCode`（JUCE 音频/MIDI/OSC）。

## 上游测试审计

- 顶层无 `enable_testing`/`add_test`，无 `tests/` 目录，无 `make check` 目标；`ctest -N` 为空。
- `external_libs/oscpack_1_1_0/tests`、`spdlog-0.11.0/tests`、`juce_core/unit_tests` 为被打包第三方的自带文件，非 osmid 上游测试，不计入总数。
- 结论：`upstream_tests_exist: false`，`upstream_test_total: 0`（口径 `ctest_entries`），`test_package/MANIFEST.yml` 已声明，真机输出 `status:"no_tests"`。

## 验证结果

```bash
# 真机预检（hmbs 后台执行，本轮未跑，待下一轮 evidence 回填）：
#   conan create archives/o/osmid/0.8.0-repack -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 预期：
#   m2o --help → exit 1 + "Bridges MIDI to OSC"
#   o2m --help → exit 1 + "Bridges OSC to MIDI"
#   HMBS_TEST_PACKAGE_RESULT discovered=4 passedCount=4
#   HMBS_UPSTREAM_TEST_RESULT status=no_tests discovered=0 executed=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/m2o` | MIDI→OSC 桥 |
| `bin/o2m` | OSC→MIDI 桥 |

## 注意事项

- 本轮仅完成未提交工作树，未做 `git commit/push`、未创建 PR、未调用 GitCode 写接口，等待 hmbs 真机 rule4 门禁。
- 真机若报 JUCE/ALSA 头缺失或链接失败，按失败日志补依赖或调补丁，旧验证即失效，需重新完整验证。
- PR 正文草稿见 `.hmbs/pr-body.md`，测试数字留待真机 evidence 轮填写。
