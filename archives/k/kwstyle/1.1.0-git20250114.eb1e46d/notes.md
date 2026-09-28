# KWStyle 1.1.0-git20250114.eb1e46d 适配笔记

**日期**: 2026-09-25
**状态**: ✅ built（本地 `conan create` 退出码 0；41 项上游 CTest 全通过；消费者用例 3/3 通过）
**分支**: `feat/kwstyle-1.1.0-git20250114.eb1e46d`
**构建系统**: CMake + CTest
**上游主页**: <https://github.com/Kitware/KWStyle>
**构建环境**: HarmonyOS PC（HongMeng Kernel 1.12.0，aarch64，musl）
  - DevBox clang 15.0.4（target `aarch64-unknown-linux-ohos`）
  - OpenHarmony SDK `ohos-sdk_26.0.0.18`（`/data/service/hnp/ohos-sdk.org/`）
  - CMake 4.1.2 / Ninja 1.13.1 / Conan 2.29.1（OHOS 适配版，社区 PyPI）
  - profile：`ci/conan/profiles/ohos-aarch64`（host/build 同 profile）

---

## 1. 版本号说明

平台任务把版本固定为 `1.1.0-git20250114.eb1e46d`，对应上游 master 上的 commit
`eb1e46d57db0`（2025-01-14，`COMP: Improve type size correctness`）。

- 上游 `CMakeLists.txt` 自身声明 `project(KWStyle VERSION 1.1.0)`；
- 该 commit 是 1.1.0 线上的最后提交；
- `KWSTYLE_VERSION_STRING` 由 `KWStyleConfigure.h.in` 从 `@KWStyle_VERSION@` 生成，
  因此 `KWStyle -version` 实测输出 `Version: 1.1.0`（不含 git 后缀）。

> 本配方**沿用平台给定版本字符串**，以保证分支名、Conan 引用、任务绑定三者一致。

## 2. 源码信息

| 项 | 值 |
|---|---|
| URL（官方） | `https://github.com/Kitware/KWStyle/archive/eb1e46d57db0.tar.gz` |
| SHA256 | `93cab9d40052a01a237525f6f25b16ac97c94ee5fd4b725fadd1f2e51dbe4eaf` |
| 大小 | 3,539,061 bytes |
| 格式 | tar.gz，根目录 `KWStyle-eb1e46d57db04a2f94a1a4709a67d8fb8f986400/` |

`conandata.yml` 只列**官方源**（R39 要求「不要手动加镜像前缀」）：CI 的
`get_mirror_list` 对 github.com 主源在构建时自动前置 `gh-proxy.com` 镜像。

> ⚠️ 实测注意：`ci/conan/build_and_test.sh` 会**把单值 `url:` 就地改写为镜像列表并落盘**
> （约 1154 行的 `replace_url`），且这一步**不在**其 `conandata.yml` 备份/还原范围内。
> 因此每次跑完本地 CI 后，`conandata.yml` 会变成
> `[gh-proxy.com/<url>, <url>]` 两元素列表；**提交前必须还原为单值官方 URL**，
> 否则会与注释自相矛盾并被审计判为 R39 偏差（本轮 W4 审计即命中此点）。
> 本机到 GitHub 直连超时，实测 `gh-proxy.com` 可用。

## 3. 依赖分析（W0 结论）

**零外部 Conan 依赖。** 依据：对源码树全文检索 `find_package|find_library|find_program`
（CMakeLists.txt / CMake/ExportConfiguration / Utilities / Utilities/KWSys）→ 无命中。

随源码 vendored 的 KWSys（`Utilities/KWSys`）由 `Utilities/CMakeLists.txt` 配置为静态库
`kwssys`，与 `KWStyleLib` 一起链接进可执行文件。因此**不存在依赖链断裂风险**。

## 4. 构建配置

```python
tc.variables["BUILD_SHARED_LIBS"] = "OFF"        # R26 终端工具静态构建
tc.variables["BUILD_TESTING"] = "ON"             # 打开 Testing/ 子目录
tc.variables["CMAKE_CXX_STANDARD"] = "11"        # 对齐上游默认值
tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
tc.variables["CMAKE_CXX_EXTENSIONS"] = "OFF"
tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"       # ★ 必须，见 §5.1
tc.preprocessor_definitions["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"] = "1"  # ★ 见 §5.2
```

`package_type = "application"`：产物是 `bin/KWStyle`。`package()` 中剥离
`cmake/`、`include/`、`lib/` 等内部开发文件（KWStyleLib/kwssys 为内部静态库，头文件仅供
自身编译），包内只保留用户需要的 `bin/KWStyle`（实测打包 1 个二进制 + 2 个 .xml 示例规则
+ 2 个 .h 头 + 1 个 logo）。

## 5. 三个必须解决的问题（均为实测定位）

### 5.1 KWSys 误选 Windows 实现 → `windows.h file not found`

**现象**：编译早期报
```
Utilities/KWSys/ProcessWin32.c:27:10: fatal error: 'windows.h' file not found
```

**根因（对应知识库 E577）**：本机 `uname -s` 返回 `HarmonyOS`，CMake 因此取
`CMAKE_SYSTEM_NAME=HarmonyOS`（实测 CMakeSystem.cmake 确认）。但 CMake 只随带
`Modules/Platform/OHOS.cmake`（内容仅一行 `include(Platform/Linux)`），**没有**
`Platform/HarmonyOS.cmake`（实测 cmake 4.1.2 下该文件不存在）。平台模块不加载 →
`UNIX`、SONAME flag、`find_package(Threads)` 等 POSIX 语义全部未定义，
CMake 仅打印 `System is unknown to cmake`（**不是错误、退出码仍为 0**）。

KWSys `Utilities/KWSys/CMakeLists.txt` 用平台布尔变量选实现：
```cmake
if(KWSYS_USE_Process)
  if(NOT UNIX)
    set(KWSYS_C_SRCS ${KWSYS_C_SRCS} ProcessWin32.c)   # ← OHOS 上误入此分支
  else()
    set(KWSYS_C_SRCS ${KWSYS_C_SRCS} ProcessUNIX.c)
  endif()
endif()
```

**修复**：`generate()` 中显式 `tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"`，平台真名生效，
`Platform/OHOS.cmake` → `include(Platform/Linux)` → `UNIX` 为真。
实测修复后日志出现 `Building C object .../ProcessUNIX.c.o`，编译通过。
仓库同口径先例：`archives/a/astromenace`、`archives/a/avogadrolibs`、`archives/d/dbus`。

### 5.2 OHOS musl 无 pthread_setcancelstate（E507 / E099）

**现象**：
```
Utilities/boost/core/detail/sp_thread_sleep.hpp:73:5: error: use of undeclared identifier 'pthread_setcancelstate'
```

**根因**：KWStyle 自带的 boost 经 `boost/shared_ptr.hpp` → `spinlock_pool` → `yield_k`
→ `sp_thread_sleep.hpp` 间接包含该头。OHOS musl 不实现 POSIX 线程取消 API。
上游该头的守卫为 `#if defined(BOOST_HAS_PTHREADS) && !defined(__ANDROID__)` ——
已为 Android（同样缺该函数）留了例外，但**未覆盖 OHOS**。

**修复（两步，均不使用平台宏）**：

1. `patches/0001-boost-sp-thread-sleep-skip-pthread-setcancelstate.patch`
   给 3 处守卫补上 `&& !defined(BOOST_SP_NO_PTHREAD_SETCANCELSTATE)`；
2. `generate()` 定义该能力宏，跳过 `pthread_setcancelstate` 调用但**保留 nanosleep**。

> 知识库 E507 明确 `forbid_1_pattern: __OHOS__|HarmonyOS|pthread_setcancelstate.*stub`
> —— 禁止平台名分支与空壳 stub（会曲解目标能力、改变取消语义）。上述做法只引入
> **能力宏**，无任何平台名，符合 R8 与 E507。
> 同口径、且自述 "R8-compliant (no platform macro)" 的既有先例：
> `archives/b/boost-1.85/1.85.0-b2-nodocs/patches/0001-ohos-pthread-cancel-fix.patch`；
> 另见 `archives/a/afmize`、`archives/a/autodock-vina`。

### 5.3 隐蔽问题：include-guard 检查被构建路径静默禁用 → Test5059 失败

**现象**（修复 §5.1/§5.2 后）：`ctest` 报
```
31/41 Test #31: Test5059 ... ***Failed
The baseline as more errors than the test
98% tests passed, 1 tests failed out of 41
```

**根因**（本条为本轮新发现，知识库暂无对应条目）：
上游 `kwsCheckIfNDefDefine.cxx` 开头用**整条路径的子串**判断是否跳过 C 源文件：
```cpp
// Check only if we are not a .cxx or .cc or .c file
if(m_Filename.find(".c") != std::string::npos)
  {
  return false;
  }
```
Conan 2 的源码/构建路径位于缓存根 `~/.conan2` 之下，其中**就含子串 `.c`**
（`.conan2`）。于是该条件恒为真，include-guard 检查对**所有文件**（包括 .h）被静默跳过。

**为什么只有 Test5059 暴露**：`KWStyleTests` 的比对器 `Compare()` 只有在
「测试输出仍有错误、而基线剩余更多错误」时才判失败；若测试输出**完全没有** `<Error>`，
则 `posError` 与 `posErrorBase` 均取 `-1`、循环被跳过，直接返回 0 = **假通过**。
`Testing/Data/` 中只有 `5059-output.xml` 期望 NDEFINE（ErrorNumber 14）这条，
其余 40 项要么不含该检查、要么空输出假通过，所以 41 项里只有 5059 挂。

**定位过程（可复核）**：
```bash
# 实际输出比基线少第 5 条 Error（ErrorNumber 14 = NDEFINE）
diff Testing/Data/5059-output.xml <build>/5059-output.xml
# 把测试数据复制到不含 ".c" 的路径下重跑 → 输出与基线逐条一致
```

**修复**：`patches/0002-kwsCheckIfNDefDefine-test-file-extension-not-path.patch`
把判断从「路径子串」改为「**文件扩展名**」（`.c/.cc/.cxx/.cpp/.c++`），保留上游
「跳过 C/C++ 源文件」的本意，同时不再受父目录名影响。
行为差异仅限「路径中含 `.c` 的头文件」，其余扩展名判定与原先一致；
实测修复后 `Test5059` 输出与基线 5/5 条 `Error` 完全一致并判 Pass。

## 6. 测试结果（实测）

### 6.1 上游 CTest：41/41 通过（100%）

```
100% tests passed, 0 tests failed out of 41
Total Test time (real) =   2.03 sec
```

| 类别 | 数量 | 来源 |
|---|---|---|
| 单元测试 | 6 | `Testing/KWStyleTests.cxx` `RegisterTests()` 中前 6 个 |
| bug 基线对比测试 | 35 | `ADD_TEST_FROM_BUG_TRACKER()`（kwsRunKWStyleTest 驱动） |
| **合计** | **41** | |

> **未修改任何上游测试用例与基线**：`Testing/` 与 `Testing/Data/` 全部保持原样，
> 两个补丁都只改产品代码/第三方头文件（`kwsCheckIfNDefDefine.cxx`、boost 头）。

### 6.2 消费者用例：3/3 通过

```
=== KWStyle consumer verification ===
PASS 1/3: -version -> Version: 1.1.0
PASS 2/3: 错误检出 -> exit=1, 2 个 <Error>
PASS 3/3: 干净文件通过 -> exit=0
test kwstyle 1.1.0-git20250114.eb1e46d: 3/3 checks PASS
```

以「库的使用者」身份调用已安装的 KWStyle 命令，验证可观测行为（R34）：
① `-version` 输出；② 对含制表符+超长行的 `bad.cpp` 必须报错且导出 XML 含 `<Error>`；
③ 对干净的 `good.cpp` 必须 exit 0。断言依据上游 `kwsStyle.cxx` 的退出码语义
（`if(nerrors > 0) return EXIT_FAILURE;`）。

> 注：上游 CLI 使用**单横线**选项（`-version`、`-h`、`-xml`），不是 `--version`；
> 且 `-version`/`-h` 分支走 `MetaCommand::Parse()` 返回 false → `main` `return 1`，
> 故版本断言只校验输出内容、不校验退出码。

### 6.3 复现命令

```bash
conan create archives/k/kwstyle/1.1.0-git20250114.eb1e46d \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 7. 已知旁证与注意事项

- 构建日志出现 `make: jobserver mkfifo: .../GMfifoNNNNN: Operation not permitted`
  —— HMDFS 不允许创建 jobserver fifo（知识库 E074 同类）。本次为**非致命警告**，
  构建以 `-j20` 正常完成，故未按 R9 强制 `-j1`。
- `Problem parsing /proc/meminfo` 为 CMake 在 HarmonyOS 上的既有提示，非致命。

## 8. 未做/后续

- 未上传制品仓（`commands.json` 的 `binary` 保持 `false`），待 finish/release 流水线处理。
- `KWStyle -version` 输出为 `1.1.0`（不含 git 后缀），与平台任务版本字符串的差异已在 §1 说明。
- 本轮发现 §5.3 的「路径子串判断」问题在知识库中暂无条目；按路径 A 约束本次未改动
  `knowledge/`，仅在此记录，供后续路径 B 立项参考。

## 9. 许可证判定（W4 审计 P1 修正记录）

**修正时间**：2026-09-25（W4 独立审计提出 P1 后复核修正）

初版配方误将 `license` 写为单一 `Apache-2.0`。经对 pin 住的 commit `eb1e46d57db0`
源码树**实地核对**，该声明与上游不符，已更正为复合 SPDX。

**核对证据**（源码树 `KWStyle-eb1e46d57db04a2f94a1a4709a67d8fb8f986400/`）：

| 组件 | 许可证文件/头 | 文件数 | SPDX |
|---|---|---|---|
| KWStyle 产品源码 | 根目录 `Copyright.txt`（Kitware BSD 式：3 条 BSD 条款 + 「修改版须显著标注」条款），源码头写 "See Copyright.txt" | 38 个 `.cxx`/`.h` | `BSD-3-Clause` |
| `metaCommand.cxx` / `metaCommand.h` | Apache-2.0 头（Copyright NumFOCUS） | 编入 `bin/KWStyle` | `Apache-2.0` |
| `Web/headers/ITKHeader.h` | Apache-2.0 头 | 随包安装到 `share/KWStyle/headers/` | `Apache-2.0` |
| vendored KWSys（`Utilities/KWSys`） | `Copyright.txt`（Kitware BSD） | — | `BSD-3-Clause` |
| vendored boost（`Utilities/boost`） | 头文件内声明 Boost Software License | 3804 个头文件 | `BSL-1.0` |

> 另：`kwsHeader.h` 亦带 Apache-2.0 头，但**既不被任何 `.cxx` 包含（不参与编译）、
> 也不随包安装**，故不计入交付产物的许可构成。

- 上游根目录**没有 `LICENSE` 文件**，只有 `Copyright.txt`；GitHub API 对该仓库返回
  `license = Other / NOASSERTION`。
- `metaCommand.*` 被编入 `bin/KWStyle`（`KWStyleLib` 成员），且
  `share/KWStyle/headers/ITKHeader.h` 随包安装，故 `Apache-2.0` 是
  交付产物的一部分，不能省略。
- vendored boost 仅使用其中少量头（`boost/core/*`、`shared_ptr`、`spinlock`、
  `sp_thread_sleep`），但均以 `BSL-1.0` 授权，需一并声明。

**最终声明**（三处保持一致：`conanfile.py` 的 `license`、软件级 `manifest.yaml` 的
`license`、`README.md` 的「许可证」段）：

```
BSD-3-Clause AND Apache-2.0 AND BSL-1.0
```

> 说明：复合 `AND` 表达式是本包的真实许可组合；仓库内已有先例
> （如 `BSD-3-Clause AND LGPL-3.0-only AND GPL-3.0-only`）。
> 单一 `Apache-2.0` 会随制品仓/SPDX 扫描向下游误传许可条件，故必须修正。

**顺带上报上游建议**：`kwsCheckIfNDefDefine.cxx` 的「路径子串判断」缺陷（§5.3）
对任何构建路径含 `.c` 的使用者都成立，建议向上游提 issue/PR。
