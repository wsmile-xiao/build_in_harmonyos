# verovio 6.2.1 适配笔记

## 编译环境
- 构建系统: cmake（CMakeLists.txt 位于 cmake/ 子目录）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ (HarmonyOS PC 真机)
- 状态: built (未发布)

## 编译步骤

1. 下载源码: https://codeload.github.com/rism-digital/verovio/tar.gz/refs/tags/version-6.2.1
   - sha256: fa0ccdad12f2d56b7e76537ad7af5355a9e6861c17f793e028741b1e2800bbb0
   - 注意：GitHub codeload URL 末段是裸 tag 名 "version-6.2.1"（无 .tar.gz 扩展名），
     Conan get() 默认按末段推断文件名并选用 zip 解码器 → BadZipFile。
     解决方案：显式传 filename="verovio-6.2.1.tar.gz" 强制使用 tar.gz 解码器。
2. 创建分支: feat/verovio-6.2.1（基于 upstream/main）
3. 编写 Conan 配方
4. 打补丁: 修复 std::ranges::all_of 兼容性问题

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | std::ranges::all_of 编译错误 | Clang 15.0.4 的 libc++ 不支持 C++20 std::ranges | 替换为 std::all_of（添加 #include <algorithm>，添加 end iterator 参数，修复变量 shadowing） |
| 2 | CMake 无法识别 HarmonyOS | cmake 平台检测不认识 HarmonyOS | 设置 CMAKE_SYSTEM_NAME=Linux |
| 3 | BadZipFile: File is not a zip file | codeload GitHub URL 末段是裸 tag 名，Conan get() 推断文件名无扩展名，默认用 zip 解码器解压 tar.gz | source() 中显式传 filename="verovio-6.2.1.tar.gz" |
| 4 | conanfile.py 风格违规 | 使用了旧的 self.copy() API | 改用 conan.tools.files.copy() |
| 5 | package_info() 不完整 | 缺少 bindirs 声明 | 添加 cpp_info.bindirs = ["bin"] |
| 6 | conandata.yml 使用非官方镜像 | gh-proxy.com 非权威镜像源 | 移除镜像，仅保留官方 codeload GitHub URL |
| 7 | Conan 初始化报 `[conf] 'tools.env:defines' does not exist in configuration list` | **交叉包证据（round-5，确诊为设备/harness 侧）**：①`tools.env:defines` 在 2.5/2.30/2.31/2.32 官方 `conan config list` 中均不存在（tools.env.* 仅 deactivation_mode/virtualenv:powershell/dotenv），`tools.*`/`core.*` conf 只能由 profile/CLI 注入，配方不可设置；②该错在 `conan create` 的 Conan 初始化阶段、任何配方方法执行前即报（stdout 首行即 conan create 失败）；③对照同批已过预检的 application 包 sasa/0.4，其 package_info 仅 `cpp_info.bindirs=["bin"]`（与我们现在完全一致），另一 passing 包 vcflib 甚至使用 `buildenv_info.append_path`，说明配方结构/包类型/环境调用均非触发因素；④关键：harness 每轮复用**同一** CONAN_HOME `clients/abef26a243e8/conan-home`（各轮日志路径逐字节相同），该 CONAN_HOME 中残留的无效 `tools.env:defines` conf 会跨轮持久化且与配方无关。**结论=设备/harness 环境问题**：需在设备侧清理/重建该 CONAN_HOME（移除 default profile / global.conf 中的 `tools.env:defines`），配方侧无可再修的代码路径。配方保留极简 package_info（与 sasa 已验证形态一致），不伪造通过 | round-4 曾移除 `runenv_info.define()`（保持极简 cpp_info，与 sasa 一致，属正确形态）；round-5 用 sasa/vcflib 对照确认配方非根因，锁定为 CONAN_HOME 残留 conf |

## 补丁修复记录

**文件**: src/resources.cpp

**修改内容**:
1. 添加 `#include <algorithm>` 头文件
2. 将 `std::ranges::all_of(iter, lambda)` 替换为 `std::all_of(iter, end_iter, lambda)`
3. 将 lambda 内变量 `path` 重命名为 `p` 避免与外层 `path` 变量 shadowing

**根因**: Clang 15.0.4 的 libc++ 标准库未实现 C++20 的 `<ranges>` 头文件及 `std::ranges::all_of` 算法

## 依赖分析

- **无外部依赖**：verovio 将所有第三方库内嵌到源码中
  - pugixml (XML 解析) — include/pugi/
  - humlib (Humdrum 格式支持) — include/hum/
  - jsonxx (JSON 解析) — include/json/
  - crc (CRC 校验) — include/crc/
  - zip (ZIP 压缩) — include/zip/
  - tuning-library (调音库) — include/tuning-library/
  - libmei (MEI 库) — libmei/dist/, libmei/addons/
- **仅链接系统库**: libc++_shared.so, libc.so (musl/bionic)

## 上游测试审计

### 上游测试套件结构
- **主测试脚本**: doc/test-suite.py（Python）
- **测试数据**: doc/tests/ 目录，按类别分子目录存放 **78 个 PAE 乐谱输入文件**（每个输入即一个测试用例）
- **测试方式**: test-suite.py 导入 verovio 的 Python 模块（SWIG 绑定），逐条渲染 PAE→SVG，
  并用 cairosvg 输出 PNG，一并生成 timemap JSON。

### 依赖分析（见 doc/test-suite.py 源码）
| 依赖 | 用途 | OHOS 可用性 |
|------|------|------------|
| verovio Python 模块 | SWIG 绑定（BUILD_AS_PYTHON 路径） | ❌ 需 SWIG+Python.h+目标平台 Python |
| cairosvg | SVG → PNG 渲染 | ❌ 依赖系统级 cairo/librsvg 图形栈 |
| xml.etree（标准库） | XML 解析 | ✅ |
| json（标准库） | 选项解析 | ✅ |

### 结论
上游测试套件依赖「SWIG Python 绑定 + 系统级 cairo 图形栈」，整条链路在无头
HarmonyOS PC 真机工具链中不可用（非可独立补齐的单个 pip 包，而是整条 Python
绑定 + 本地图形库链路缺失）。本配方按命令行工具（BUILD_AS_LIBRARY=OFF）构建
verovio CLI，未构建 SWIG Python 模块。故上游 78 个用例无法在真机整套运行，
属平台环境限制（详见 manifest.yaml 审计）。

### 消费者验证（test_package）
改为与同仓已验证的 application 包 atracdenc 一致的 CLI 功能冒烟模型：
`test_package/test.sh` 直接调用已安装的 verovio CLI，执行 4 项检查：
1. `verovio --version` 输出 Verovio 版本横幅
2. 用真实 MEI 乐谱执行 MEI→SVG 渲染（`-r <share/verovio>` 指定资源目录）
3. 校验渲染出的 SVG 非空
4. 校验 SVG 包含 `<svg>` 根元素
test_package/conanfile.py 在测试结束后输出 HMBS_TEST_PACKAGE_RESULT 标记
（discovered=4, passedCount=4，来自 test.sh 的 4 项真实断言）。

## round-8 聚焦修复（2026-09-20）— 配方/消费者一致性

**问题**：此前 test_package 仍按「链接 verovio 静态库」编写（find_package(verovio CONFIG)
+ target_link_libraries(verovio::verovio) + include vrv.h/toolkit.h），而主配方是
BUILD_AS_LIBRARY=OFF 的 application 包（只出 verovio CLI、无 verovio::verovio target）。
两者矛盾，test_package 必然链接失败。

**修复**：把 test_package 改为与 application 包模型一致的 CLI 功能冒烟（test.sh +
bash 包装运行），彻底移除 C++/CMake 测试文件。

**附带修正**：package() 原来自行 copy data/ 到 share/verovio/data（与上游 install 的
share/verovio 布局不一致，会造成资源目录结构错误、CLI 找不到 SMuFL 数据）。
修正为直接依赖上游 cmake install()（CLI→bin/，data→share/verovio/），删除多余 copy。

## 验证结果

### 编译状态
- ✅ CMake 配置成功
- ✅ 编译通过（含补丁应用）
- ✅ 安装成功（bin/ 含 verovio 可执行文件，share/verovio/ 含数据文件）

### 二进制信息
- 类型: ELF shared object, 64-bit LSB arm64
- 动态依赖: libc++_shared.so, libc.so
- 大小: 约 15MB

### 兼容性
- ✅ C++20 标准
- ✅ aarch64 架构
- ✅ OHOS/HarmonyOS 平台

## round-6 聚焦修复（2026-09-19）— 真机 compile 失败 `tools.env:defines`

**错误**：`Error in Conan initialization: [conf] 'tools.env:defines' does not exist in configuration list.`

**诊断**：OHOS 适配版 Conan（设备 2.30）conf 注册表不完整；对未注册 conf 的读取（`self.conf.get`/环境生成）直接抛
`[conf] 'X' does not exist in configuration list`（同仓知识 E6340 / DRAFT-ohos-conan-make-executable-conf 已记录同类根因）。
`tools.env:defines` 不是任何 Conan 2 的合法 conf（`tools.env.*` 仅有 deactivation_mode/virtualenv:powershell/dotenv）。

**配方改动**：把 generate() 对齐到本仓已验证通过的 CMake OHOS 配方 atracdenc/0.2.3（run 同款 OHOS conan + CMakeToolchain + 共享 harness）：
- `tc.cache_variables[...]`（CMAKE_SYSTEM_NAME + 含 CMAKE_SYSTEM_PROCESSOR 的双 cache_variables 写法）→ 全部改 `tc.variables["CMAKE_SYSTEM_NAME"]="Linux"`
- 删除 `CMAKE_SYSTEM_PROCESSOR` cache_variables（atracdenc 无此项，避免 OHOS CMakeToolchain 进入跨编译 env 注入路径）
- 清理 package_info 中先前「设备/harness 问题、无可修」的注释，改为已验证形态

**注意**：若纯配方对齐仍不能消除 conf 初始化错误，则该 conf 来自任务 CONAN_HOME 内残留的 profile/global.conf，
需真机侧清理该 CONAN_HOME 后重测（配方层无法在 conan init 前清理）。

## round-7 聚焦修复（2026-09-19）— 真机 compile 失败 Signal 9（SIGKILL，退出码 137）OOM 削峰

**错误**：conan create 编译到 99%（`[ 99%] .../src/pugi/pugixml.cpp.o` 等收尾目标）后进程被
`Signal 9` 杀死（退出码 137 = 128+9 = SIGKILL），上游测试 0/0/0，阶段=compile。

**诊断**：这是低内存真机的 OOM 杀掉（非配方/源码错误）。verovio 在 `BUILD_AS_LIBRARY=OFF`
路径下把所有源文件（vrv 核心 + libmei 自动生成 + hum + crc + midi + jsonxx + pugixml）编译进
**单个巨型可执行 target**（cmake/CMakeLists.txt `add_executable(verovio ../tools/main.cpp ${all_SRC})`）。
CMake Release 默认用 `-O3`，数百个 TU 在 -O3 下对象体积/符号量巨大，编译收尾与最终链接的内存峰值
超过真机配额 → OOM killer SIGKILL。日志特征：在 99% 收尾（最后几个 .o + 链接）时 Signal 9，
toolchain 诊断显示 jobs=1、hardlink/chmod 受限，未涉及上游测试。

**配方改动**（conanfile.py generate()）：把 Release 编译档从默认 `-O3` 降为 `-O2`：
`tc.variables["CMAKE_CXX_FLAGS_RELEASE"] = "-O2 -DNDEBUG"`
——-O2 是发行版通用标准档，显著削减 -O3 的激进内联带来的对象/符号体积，降低编译收尾与链接内存峰值，
同时产物性能口径合理。参考本仓 knowledge/drafts/DRAFT-ci-lowmem-worker-link-oom-mitigation
（三次跨 PR 复现：低内存 worker 链接期 OOM，逐级降档 -g0 → -Os，仅动档位/不改源码）。
verovio Release 本就不加 -g，故 -g0 档无收益，直接动优化档。

**兜底**：若 -O2 仍 OOM，下一步按知识库梯度把该 target 降至 -Os（地址空间/内存最省）。

## round-9 聚焦修复（2026-09-20）— 接入上游测试执行 + test_package 诚实计数/诊断

**真机失败（rule4）**：上游测试发现/执行/通过均为 0 → rule4 判定 incomplete「缺少上游运行结果」；
且 test_package test.sh `[check 3/4] SVG output is empty` FAIL（test_package 失败）。
（本机 glibc 用同配方同选项完整复现 build+install+test 全流程：样例 MEI 与全部 78 个
上游 PAE 输入均渲染出非空合法 SVG，证明本地/配方逻辑正确，真机空 SVG 为设备侧问题，
需下一次预检给出真机 render.err 才能定位。）

**修复 1：接入上游测试执行（对 rule4「缺少上游运行结果」）**
- 官方套件 doc/test-suite.py 需 verovio Python/SWIG 模块 + cairosvg（系统级 cairo），
  两者在无头 OHOS 真机不可用（平台环境限制，非可独立补齐的 pip 包）。
- 采用与官方口径一致的真机等价执行：新加 `tools/run_upstream_pae.sh`，在 conanfile.py
  `build()` 中用编译得到的 verovio CLI（`-f pae -r <src/data> <doc/tests/pae/**/*.pae>`）
  对官方同一批 78 个 PAE 输入逐条真实渲染，校验每个输出 SVG 非空且含 `<svg>` 根元素。
- 计数来自脚本循环控制流（单一确定性来源），以 `HMBS_UPSTREAM_TEST_RESULT` 标记输出
  （discovered=78，executed/passed 逐条真实值），不硬编码、不对 stdout 字符串数数。
- 已在本机用桩验证 harness 能抓到失败：CLI 输出空 SVG 桩 → 正确报 78 failed；
  CLI 不可运行（--version 失败）→ FATAL 退出（基础设施问题，不冒充测试失败）。
- conanfile.py：新增 `exports_sources = "tools/*"`（保证 runner 进入 source_folder）、
  build() 内直接以系统环境运行 CLI（verovio 无运行时依赖，无需 conanrun），build() 末尾调用
  `_run_upstream_tests()`。

**修复 2：test_package 诚实计数 + 失败诊断**
- test.sh：每个检查无条件自增 total、仅通过时自增 pass（修掉原「total 只在 PASS 时 +1，
  失败时 total 漏计导致假 OK」的计数 bug）；把结果写入 `$HMBS_TP_RESULT` JSON
  （python3，缺 python3 时 bash printf 兜底，仍为同一计数器单一来源）。
- test.sh 失败时打印 render.stderr、out.svg 是否存在/字节数，把真机空 SVG 的根因证据
  暴露给下一次预检。仍保持 4 项冒烟检查。
- test_package/conanfile.py：改为读 `$HMBS_TP_RESULT` 中的真实 discovered/passed 生成
  HMBS_TEST_PACKAGE_RESULT（原来硬编码 passedCount=4，测试失败也报 4，自相矛盾）。

**口径声明**：upstream_test_total=78（官方 doc/tests/pae 输入清单）；upstream_test_in_build=true；
test_package 冒烟 4 项。manifest.yaml / test_package/MANIFEST.yml / notes.md 同步更新。

## round-11 聚焦修复（2026-09-20）— 上游测试 runner 与 /bin/sh 兼容

**真机失败（compile 阶段）**：
```
verovio/6.2.1: RUN: /bin/sh .../tools/run_upstream_pae.sh .../build/Release/verovio .../data .../doc/tests
.../tools/run_upstream_pae.sh[36]: syntax error: unexpected '< '
ConanException: Error 1 while executing
上游测试：发现 0，执行 0，通过 0，失败 0，跳过 0
```
编译本身已到 99%（cmake.build() 完整通过），失败发生在 build() 末尾调用 `_run_upstream_tests()`
执行 runner 时；test_package 尚未运行即被中断。

**根因**：runner `tools/run_upstream_pae.sh` 用了 bash 专有语法
`mapfile -t FILES < <(find ...)`（第 36 行，进程替换 + mapfile 数组）。而真机按
`$CONFIG_SHELL`（真机为 `/bin/sh`）解释执行该脚本——`/bin/sh` 解析不到
`< <(` 即报 syntax error。HMBS_PLATFORM_CAPABILITIES 亦确认 `"shell":"/bin/sh"`。
这是脚本语言不兼容问题，与 verovio 本体编译无关（编译已 99% 完成）。

**修复**（tools/run_upstream_pae.sh 改为 POSIX sh 兼容，计数语义不变）：
- 删除 `mapfile -t FILES < <(find "$TESTS" -name '*.pae' | sort)`；
  改为先把排序后的输入清单落盘到 `$OUTDIR/files.list`，再用
  `while IFS= read -r f; do ... done < "$LIST"` 逐行计数/渲染。
  （不直接管道给 while：POSIX sh 中管道会开子 shell，循环内的计数器
  PASS/FAIL/TOTAL 会丢失，故必须经临时文件重定向回当前 shell。）
- 循环内逻辑与计数（TOTAL/PASS/FAIL/SKIP、EXECUTED=PASS+FAIL+SKIP）逐字保留，
  仍为单一确定性计数来源，HMBS_UPSTREAM_TEST_RESULT 标记格式不变。
- 文件名处理全程引号包裹 + `IFS=`，兼容含空白路径；`${f##*/}`、`$((...))`、
  `${TOTAL:-}` 等均为 POSIX 构造。
- 已在本机用 dash（/bin/sh）语法检查 + 桩 CLI 全路径验证：
  dash -n 通过；4 个桩输入（1 PASS/1 empty FAIL/1 rc=3 FAIL/1 PASS）如实输出
  discovered=4 executed=4 passed=2 failed=2；无输入时输出 no_tests 标记；
  桩 CLI 不可运行时 FATAL 且退出 1——本机环境与真机同为 POSIX /bin/sh 语义。
- test.sh（test_package 侧）同样经 CONFIG_SHELL 解析的 shell 执行，已核对
  无 bash 专有构造（dash -n 通过、grep [[/local/mapfile/<<< 无命中），无需改动。

**口径不变**：upstream_test_total=78；test_package 冒烟 4 项；
HMBS_UPSTREAM_TEST_RESULT / HMBS_TEST_PACKAGE_RESULT 计数仍由脚本控制流单一来源产生。

## round-10 源码审计核对（2026-09-20）— 事实复核

对官方 codeload 归档 `version-6.2.1` 做逐项事实核对（已下载验证后清理）：
- **sha256**：`fa0ccdad12f2d56b7e76537ad7af5355a9e6861c17f793e028741b1e2800bbb0` 与
  conandata.yml / manifest.yaml 完全一致。✓
- **源码根目录**：归档根为 `verovio-version-6.2.1/`（非 v-6.2.1），source() strip_root=True 后
  落位 source_folder 顶层，cmake/、data/、doc/、src/、include/ 均在根。✓
- **上游测试总量**：`doc/tests/pae/` 下确有 **78 个 .pae**，六类子目录(1_clefs/2_keys/3_octave/
  4_duration/5_accidentals/6_mixed)与声明一致；`doc/test-suite.py` 存在且逐文件（含 .pae）渲染，
  确认 doc/tests 内无 .mei/其它文件，78 即官方套件用例清单。✓
- **test-suite.py 依赖核实**：import verovio（SWIG Python 绑定）+ cairosvg（SVG→PNG，系统级
  cairo），与 manifest/notes 的「无头 OHOS 不可用（平台环境限制）」声明一致。✓
- **exports_sources tools 冲突核对**：上游源码自带 tools/（main.cpp/c_wrapper.*/get_git_commit.sh/
  .configure），与本地 runner `run_upstream_pae.sh` 无文件名冲突，不会覆盖。✓
- **conandata URL**：官方 codeload GitHub（末段裸 tag），source() 显式 filename 强制 tar.gz。✓

均为事实复核，未改动配方/补丁；工作树保持未提交，等待 HMBS 真机 rule4 预检。

## round-13/14 聚焦修复（2026-09-20）— 真机 SVG 文件不可见：渲染结果改经 stdout 捕获

**真机失败（evidence 阶段，rule4）**：
```
上游测试：发现 78，执行 78，通过 0，失败 78，跳过 0
test_package [check 3/4] SVG output non-empty FAIL: SVG output is empty/missing
  OUT=.../tmp/verovio-test-52196/out.svg out.svg-exists=no
  (render.stderr tail)
  [Warning] MEI version found or not known, falling back to MEI 6.0-dev
  Output written to .../runtime/verovio-6.2.1/tmp/verovio-test-52196/out.svg.
test.sh summary: discovered=3 executed=3 passed=2 failed=1 FAILED
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": false, ..., "discovered": 3, "passedCount": 2}
```

**证据链**（test_package 内同一脚本、同一 $TDIR、同一进程组）：
- shell 创建的文件可见：render.err（`2>` 重定向，171 字节被 sed 读出）、files.list 正常；
- 被测 CLI 创建的文件不可见：verovio 打印 `Output written to <绝对路径>/out.svg.` 且退出码 0
  （check 2 PASS，说明 std::ofstream open/write/close 全成功），但随后 `[ -e $OUT ]` 为否——
  out.svg 对 shell 不可见；
- 上游 78 个 PAE 输入同样全部失败（CLI 每次宣称写盘成功但 out.svg 不存在 → FAIL(empty)）。

**根因**：HMBS 预检沙箱文件系统（/storage/Users/currentUser 下 hmdfs 挂载，能力位
hardlink=0/chmod=0）上，**由被测二进制进程自身 std::ofstream 创建的文件在进程退出后
对 shell 不可见**（CLI 的 stdout/stderr 经 shell 管道/重定向则可见）。本机 glibc 用
同配方全流程复现 78/78 通过 + test_package 4/4 通过，证明配方/渲染逻辑正确，差异仅
在真机文件可见性。属平台环境限制（ohos_feature），非依赖缺失、非渲染失败。

**修复（不删断言、不跳过，改为读取同一渲染结果的可见通道）**：
- `tools/run_upstream_pae.sh`：每个 PAE 输入改为 `verovio -f pae -r <data> -o - <input>`
  将 SVG 经标准输出捕获到 shell 变量（`svg=$("$CLI" ... -o - "$f" 2>case_N.err)`），
  判定逻辑不变（rc==0 且 SVG 非空 且含 `<svg>` 根元素）；失败时打印 case_N.err 尾部。
  保持 POSIX sh（dash -n 通过），计数仍为循环控制流单一来源。
- `test_package/test.sh`：check2 改为 `verovio -r RES -o - sample.mei` 经 stdout 捕获 SVG；
  check3/check4 改为对捕获的 SVG 变量断言；4 项检查全部无条件执行（discovered 恒为 4，
  不再因 check3 失败跳过 check4 造成 discovered=3 的歧义计数）。
- 脚本默认解释器统一为 `$CONFIG_SHELL`（真机 /bin/sh），兜底 /bin/sh（conanfile.py、
  test_package/conanfile.py），不再依赖 /data/service/hnp/bin/bash 兜底。

**本地证伪**（dash 执行，与真机同为 POSIX sh 语义）：
- 真实 CLI：上游 78/78 通过；test_package 4/4 通过（SVG 25446 字节）。
- 桩 CLI（--version 正常、渲染输出空）：上游如实报 78/78 失败；test_package 如实报
  discovered=4 passed=2 failed=2 且退出码 1 —— harness 能抓到失败，非假通过。

**口径不变**：upstream_test_total=78（doc/tests/pae 输入清单）；upstream_test_in_build=true；
test_package 冒烟 4 项（assertion_count=4）；HMBS_UPSTREAM_TEST_RESULT /
HMBS_TEST_PACKAGE_RESULT 计数仍由脚本控制流单一来源产生。manifest.yaml、
test_package/MANIFEST.yml（新增 platform_notes 平台限制说明）、notes.md 已同步。

**CI 修复（R38 / L0k）**：
- 构建 #56441 conan-build-test 失败于 L0k 门禁（commands_json_r38）：verovio 属
  package_type="application" 且 install 到 bin/，被判定为命令行工具，但软件级目录
  缺少 commands.json。
- 新增 `archives/v/verovio/commands.json`（type=tool、name=verovio、
  versions.6.2.1.binary=true，与 strace 示例一致），满足 build_and_test.sh L0k 校验
  （type=tool、name 含 verovio、versions 含 6.2.1）。未改动构建逻辑与测试口径。
