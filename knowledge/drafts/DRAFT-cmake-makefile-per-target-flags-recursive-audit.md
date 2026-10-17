# DRAFT-cmake-makefile-per-target-flags-recursive-audit：Makefile 生成器把 per-target flags.make 随源码子目录分层存放，ABI 关键编译标志自检必须递归定位

> Contributor: sea_crab（不知对不队） | Status: Draft | Updated: 2026-09-18
> Source: run lapacke64-3.12.1（Reference-LAPACK 3.12.1 的 LAPACKE C 接口 ILP64 变体适配）——run1 权威 CI FAIL（自检假阴性）→ 最小回修 → run2 全绿
> 申报：路径 B【知识库扩展】主条（Curator 判定，本 run 配额内仅 1 条）；八分类：构建系统语义；机理分层 L1（构建系统语义层）；阻塞面：构建失败（真实失败日志）
> 说明：本 .md 内嵌结构化条目全部要素（错误特征/触发条件/根因链/方案空间 rec-fallback-forbid/verification_cmd/挂钩关系）；`.kv` 与最终 Exxx 编号由知识库主编 promote 时确认，不自行编号。

## 现象

CMake **Unix Makefiles 生成器**工程（Conan CMakeToolchain 默认形态）里，配方在
`cmake.configure()` 之后读取 `flags.make` 自检 per-target 编译标志（ILP64 的
`-fdefault-integer-8`、`-fPIC`、LTO、feature 宏等硬 ABI/语义标志审计是常见配方
模式），若只用单层 glob 定位：

```python
glob.glob(os.path.join(self.build_folder, "CMakeFiles", "*", "flags.make"))
```

会**漏掉定义在源码子目录里的目标**，然后自检抛出"标志未见"类异常，构建被误杀：

```text
ConanException: Fortran 编译标志中未见 -fdefault-integer-8：BUILD_INDEX64 的
ILP64 Fortran 分支未生效（flang 应命中 CheckLAPACKCompilerFlags 兜底分支）
```

而该标志**实际已生效**——只是写在被审计目标自己的 flags.make 里，不在顶层。

本 run 实证（lapacke64/3.12.1）：run1 权威 CI 因此失败（run 日志 `tmp/ci-full-1.log`
:329-338，`conan create failed` → L1_RESULT=fail）；修复为递归 glob 后 run2 全绿
（`tmp/ci-full-2.log`），且 `tmp/ci-full-2-conan-build.log:220` 实证
`ILP64 self-check: -fdefault-integer-8 present in Fortran flags (2 个目标 flags 文件)`。

## 错误特征

- trigger_tool: conan|cmake|make
- phase: configuration（configure 后自检）/ packaging 前置自检
- error_signature: `Fortran 编译标志中未见|flags.*未见|ILP64.*分支未生效|Error in build\(\) method.*_assert.*flags|ConanException.*flags`（配方自检异常族；可按各自检文案扩展）

## 触发条件

- 构建系统：CMake Unix Makefiles 生成器，工程含 `add_subdirectory` 且被审计目标
  定义于子目录（本例 LAPACK 3.12.1 的 Fortran 主体目标 `blas64`/`lapack64` 分别
  定义于 `BLAS/SRC/`、`SRC/` 子目录）。
- 触发命令：配方 `build()` 内 `cmake.configure()` 之后执行读 flags.make 的自检
  （本例 `conan create` → CI `CI_PACKAGES=lapacke64/3.12.1 ci/conan/build_and_test.sh`）。
- 失败点：单层 glob 只命中顶层目标（常为纯 C 目标，flags.make 无 Fortran 标志）
  → 自检 ConanException → conan create failed → CI L1 fail（构建失败阻塞面）。

## 根因（机理链）

1. **工具实现证据**：CMake Unix Makefiles 生成器为每个 target 生成
   `<build>/<该 target 所在源码目录相对路径>/CMakeFiles/<tgt>.dir/flags.make`，
   目录深度**镜像源码树**——只有顶层 CMakeLists 里定义的 target 才落在
   `<build>/CMakeFiles/<tgt>.dir/`。本例 Fortran 主体目标在
   `build-release/BLAS/SRC/CMakeFiles/blas64.dir/flags.make` 等深层路径，顶层只有
   纯 C 的 `lapacke64`。
2. **全局变量视图脱钩**：上游用
   `add_compile_options($<$<COMPILE_LANGUAGE:Fortran>:...>)` 生成器表达式注入的
   标志**只体现在 per-target 落盘文件**，不回写 `CMAKE_Fortran_FLAGS` 类全局变量
   视图——所以"看全局变量"与"看单层顶层文件"两条偷懒路径都拿不到真相。
3. **失败点**：单层 glob 读到的顶层 flags.make 不含 `-fdefault-integer-8` → 误报
   "ILP64 Fortran 分支未生效"（实际生效）。
4. **归类**：构建系统语义（CMake Makefile 生成器落盘布局语义 × 配方自检读取
   路径），非上游缺陷、非 OHOS 平台差异。

## 双向风险（复发面）

同一语义制造**两个方向**的事故，且都真实可发生：

- **假阴性失败**（本 run run1）：标志其实在子目录目标上，查顶层查不到 → 误杀
  真实正确的构建，浪费一轮权威 CI。
- **假阳性放行**：自检恰好只命中带标志的顶层目标，而子目录目标漏加标志时照样
  "通过" → 静默 ABI 错位（ILP64 场景即 C 侧 int64 与 Fortran 侧 int32 混调），
  推迟到运行期数据损坏，比构建失败贵一个数量级。

**复发面**：任何"在 Conan/CMake 多子目录工程 build() 内读取生成器落盘 flags
文件自检 per-target 编译标志"的做法都会踩同一语义——与具体库无关。ILP64
（lapacke64/cblas64/openblas INTERFACE64）、`-fPIC`、LTO、`_XOPEN_SOURCE` 类
feature 宏审计均适用。

## 解决方案

### 推荐方案（rec_priority 1）：目标白名单递归 glob + fail-closed

```python
blobs = {}
for tgt in ("blas64", "lapack64"):          # 被审计目标白名单，逐个必达
    for p in glob.glob(os.path.join(self.build_folder, "**", "CMakeFiles",
                                    tgt + ".dir", "flags.make"),
                       recursive=True):
        with open(p, errors="replace") as f:
            blobs[p] = f.read()
if not blobs:
    raise ConanException("未找到目标 flags 文件——fail-closed，不静默通过")
bad = [p for p, t in blobs.items() if "-fdefault-integer-8" not in t]
if bad:
    raise ConanException("标志缺失于 per-target flags：%s" % bad)
```

要点：白名单保证"每个被审计目标都必须被找到"（缺文件即失败）；递归 glob
`**/CMakeFiles/<tgt>.dir/flags.make` 适配任意源码树深度。本 run 修复即此形态
（`archives/l/lapacke64/3.12.1/conanfile.py` 的 `_assert_fortran_ilp64_flags`）。

### 回退方案（fallback）：Ninja 生成器无 flags.make → build.ninja 全文扫描

```python
for p in glob.glob(os.path.join(self.build_folder, "build.ninja")):
    with open(p, errors="replace") as f:
        blobs[p] = f.read()
```

**权衡**：全文匹配无法区分 target 边界与作用域，只能作"标志存在于构建图"的
存在性证据，不能断言"注入到了指定目标"，仅作 Makefiles 路径不可用时的退路。

### 禁止做法（forbid，带 reason/consequence）

- ❌ 单层 glob `build/CMakeFiles/*/flags.make` 当作完整审计。
  reason：漏子目录目标；consequence：误杀真构建（本 run run1）或漏放静默 ABI
  错位（运行期数据损坏）。
- ❌ 只看 `CMAKE_Fortran_FLAGS`/`tc.variables` 全局变量不做 per-target 落盘核验。
  reason：生成器表达式注入的标志不回写全局变量视图；consequence：自检对象与
  真实编译命令脱钩，验证假象。
- ❌ 自检报错后删除/放宽自检放行。
  reason：把配置期可发现的 ABI 错位推迟到运行期；consequence：静默数据损坏。

## verification_cmd（自包含，任何人开新 shell 可跑）

```bash
# A. 最小机理探针（不依赖任何仓/run 日志；bash 于任意临时目录）
T=$(mktemp -d) && mkdir -p $T/sub && cd $T
cat > CMakeLists.txt <<'EOF'
cmake_minimum_required(VERSION 3.16)
project(probe NONE)
add_library(top INTERFACE)
add_subdirectory(sub)
EOF
cat > sub/CMakeLists.txt <<'EOF'
add_library(deep STATIC dummy.c)
target_compile_options(deep PRIVATE -fdefault-integer-8)
EOF
printf 'int x;\n' > sub/dummy.c
cmake -B build -G "Unix Makefiles" >/dev/null
echo "-- recursive:"; find build -name flags.make | sort
echo "-- single-level:"; ls build/CMakeFiles/*/flags.make 2>/dev/null || echo "(none or top-level only)"
grep -l fdefault-integer-8 $(find build -name flags.make)   # 命中 sub/CMakeFiles/deep.dir/flags.make
# 单层 glob 的可命中集合不含 sub/CMakeFiles/deep.dir —— 差集即本条知识

# B. 仓内重放（真实案例，OHOS 设备 CI）
# CI_PACKAGES=lapacke64/3.12.1 ci/conan/build_and_test.sh
#   修复前（单层 glob）→ conan create failed（自检误报，run1）
#   修复后（递归 glob）→ ILP64 self-check: -fdefault-integer-8 present (2 个目标 flags 文件)
```

## 挂钩与泛化

- principles: P-BUILD-001（平台/构建限制须正面处置而非绕过——fail-closed 自检
  即其体现）、P-CFLAGS-001（标志类操作须留可审计记录——递归 glob + 目标白名单
  即可审计形态）
- affected_scope: 任何在 Conan/CMake 多子目录工程 `build()` 内读取生成器落盘
  flags 文件自检 per-target 编译标志的项目（ILP64/INTERFACE64、`-fPIC`、LTO、
  feature 宏审计均适用）
- similar_to: E346（Makefile 生成器 SHELL=/bin/sh 被沙盒拒绝——同为 Makefile
  生成器语义族，二者并列覆盖"执行 shell 被拒"与"落盘目录深度"两个面）、
  drafts/DRAFT-conan-cmake-cache-stale-variable（验证假象族）、
  drafts/DRAFT-10251-libnfc-tools-1.8.0-automake-per-target-cppflags-empty-override
  （autotools per-target 标志族）、drafts/E547-draft-CD3B（ILP64/flang 族——
  本条正是其 ILP64 审计链的"读取路径"半边）

## 实证记录

- run lapacke64-3.12.1（Reference-LAPACK 3.12.1 LAPACKE ILP64 变体，
  `BUILD_INDEX64=ON` 使 CMake CheckLAPACKCompilerFlags 对 flang 兜底加
  `-fdefault-integer-8`）：
  - run1 权威 CI FAIL：初版自检单层 glob 顶层未命中 → 误报"ILP64 Fortran 分支
    未生效"（run 日志 `tmp/ci-full-1.log` :329-338）。
  - 最小回修（仅 conanfile.py）改为目标白名单递归 glob + Ninja 兜底。
  - run2 权威 CI 全绿：`tmp/ci-full-2.log`（L0-L5 门禁 + Build Summary 1/1）；
    `tmp/ci-full-2-conan-build.log:220` 自检命中 2 个目标 flags 文件。
  - 下游数值验证与该标志真实生效互证：test_package 8/8（含
    `sizeof(lapack_int)==8` 静态+运行期断言）、LAPACKE/example 4 演示双轮执行。
