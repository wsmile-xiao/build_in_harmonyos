# mapcode 2.5.7 适配笔记（HarmonyOS PC / aarch64）

## 1. 软件概况

| 项 | 值 |
|---|---|
| 名称 | mapcode |
| 版本 | 2.5.7（上游 tag `v2.5.7`） |
| 上游 | https://github.com/mapcode-foundation/mapcode-cpp |
| 官网 | http://www.mapcode.com/ |
| 许可 | Apache-2.0 |
| 语言 | C（库）+ C++（命令行工具） |
| 构建系统 | CMake ≥ 3.5 |
| 上游测试 | `test/unittest.c`（单个测试程序，2367 行） |
| 外部依赖 | **无**（仅 pthread + libm，均由 OpenHarmony sysroot 提供） |
| 产物 | `libmapcodelib.a`（静态库）+ `bin/mapcode`（命令行工具）+ 3 个公有头文件 |

mapcode 把地球上的任意位置编码成一段短字符串（Mapcode），并可反向解码回经纬度。
库本身是纯 C（`mapcodelib/`），命令行工具 `utility/mapcode.cpp` 是 C++ 但只使用 C 标准库
（`stdio.h/string.h/stdlib.h/math.h/ctype.h/time.h`），不使用任何 C++ 标准库组件。

## 2. W0 依赖发布检查（适配前第一件事）

```
$ bash ci/scripts/preflight_check.sh mapcode/2.5.7
[INFO] 未找到依赖声明（conanfile.py 尚未生成或无依赖）。
[OK]  预检通过（无依赖需要检查）
```

上游 `CMakeLists.txt` 只 `find_package(Threads REQUIRED)` 与 `find_library(M_LIB m)`，
两者都由 OHOS sysroot 直接满足，**不存在需要先发布的 conan 依赖**，因此不存在
R36 阻塞，也不需要捎带适配依赖包。

## 3. W0b 历史经验核验 + CI 能力矩阵

- `archives/m/mapcode/` 在 `origin/main` 中**无历史归档**（`git grep -l -i mapcode origin/main -- archives` 无命中），
  因此不存在"历史成功不可迁移"的风险，也没有可复用的历史 notes 绕坑命令。
- CI 能力矩阵对照：本项目只用 `clang` / `cmake` / `make` / `awk`/`sed`/`patch`
  ——全部在 CI 能力矩阵的 ✅ 列表内，**无需 `tool_requires` 补齐，也不属于 Rust/OCaml 类直接 `env_unsupported` 的情形**。
- 先例对齐：结构参考 `archives/j/jitterentropy-library/3.6.3`（同为"纯 C 库 + CMake + 无第三方依赖"）；
  交叉编译下的产物执行方式参考 `archives/t/tsl-ordered-map/1.1.0`。

## 4. 探索阶段实测到的问题与修复

### 4.1 `find_library(M_LIB m)` 在 OHOS NDK 上返回 NOTFOUND（阻断构建）

原始 `CMakeLists.txt` 无条件 `find_library(M_LIB m)`，然后
`target_link_libraries(... ${M_LIB})`。在 OpenHarmony NDK 上：

```
CMake Error: The following variables are used in this project, but they are set to NOTFOUND:
M_LIB
    linked by target "mapcode" ...
---
ld.lld-15: error: unable to find library -lM_LIB-NOTFOUND
```

根因：sysroot 把库放在 `sysroot/usr/lib/aarch64-linux-ohos/` 这个**目标三元组目录**下
（该目录下只有 `libm.a`，没有 `libm.so`），而 CMake 的 `find_library` 不去探测该目录。
**sysroot 里 `libm.a` 是存在的**（`ls sysroot/usr/lib/aarch64-linux-ohos | grep '^libm'` → `libm.a`），
所以正确做法是退回纯链接器标志 `-lm`，而不是改工具链。

修复（`patches/0001-*.patch`，**不含任何平台宏**，符合 R8）：

```cmake
find_library(M_LIB m)
if(NOT M_LIB)
    set(M_LIB m)
endif()
```

### 4.2 上游 install 规则不可用于打包

上游只有一条 `install(TARGETS mapcode DESTINATION /usr/local/bin)`：

- 静态库 `mapcodelib` 与公有头文件**完全没有安装**；
- 目标是**绝对路径** `/usr/local/bin`，`DESTDIR` 暂存会落成
  `<package>/usr/local/bin/mapcode`，下游拿不到标准 `bin/`。

修复：补丁改为 `include(GNUInstallDirs)` + 前缀相对安装（lib / include / bin 三处齐全）。
这同时让 CI 的 L5 产物基线检查能命中标准 `lib/`、`bin/`、`include/` 目录。

### 4.3 上游单测依赖工作目录（隐蔽的"1 error"陷阱）

`test/unittest.c` 用相对路径读 `territories.csv`。从构建目录直接启动会得到：

```
*** ERROR *** Can't read file territories.csv
0
 lines tested from territories.csv
...
Executed 245633397 tests, found 1 errors
UNIT TESTS FAILED!
```

**注意：2.45 亿条断言全过，仅因为工作目录不对就报 1 个 error 并返回非零。**
很容易被误判成"平台不兼容"。修复：注册 CTest 时显式设置
`WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/test`，
`build()` 里直接执行时也用 `cwd=` 指向同一目录。

### 4.4 `cross_building(self)` 在本项目恒为 False（最重要的环境语义坑）

`build_and_test.sh` 用 `-pr:h=$PROFILE_FILE -pr:b=$PROFILE_FILE` 传**同一个** profile，
Conan 因此认为 host 与 build settings 完全相同：

```
PROBE host  os=OHOS arch=armv8
PROBE build os=OHOS arch=armv8
PROBE cross_building = False
```

于是惯用写法

```python
if cross_building(self):
    self.run(f'qemu-aarch64 {binary}')
else:
    self.run(binary)
```

在 x86_64 构建机上会走 `else` 分支，直接执行 aarch64 产物：

```
aarch64-binfmt-P: Could not open '/lib/ld-linux-aarch64.so.1': No such file or directory
```

即"明明在交叉编译，却按原生执行处理"。本包改为**以构建机 CPU 为准**判断：

```python
return cross_building(self) or platform.machine().lower() not in ("aarch64", "arm64")
```

并配合 `-static`（见 4.5），使显式 qemu 路径与 CI 原生路径都能跑通。

> 注：`archives/t/tsl-ordered-map/1.1.0` 用的正是 `cross_building()` 判定，
> 在同样的 profile 下该分支永不触发，实际是靠 `binfmt_misc` 兜底才通过的。
> 本包不依赖 `binfmt_misc`，qemu 是显式调用的。

### 4.5 产物静态链接

`-static` 加在 `extra_exelinkflags`（仅链接期，不污染编译期）：

- sysroot 只有 `libm.a`，静态链接天然规避共享 libm 缺失；
- 静态 aarch64 可执行文件在 `qemu-user` 下**无需设备根文件系统**即可运行
  （已实测：`qemu-aarch64 ./unittest` 直接跑完 2.45 亿条断言）。

CI 上构建机本身即 aarch64 OpenHarmony 设备，原生执行，静态链接同样无碍。

## 5. 上游测试清点与实测（R51 三步法）

### 5.1 清点（上游 v2.5.7 源码树）

| 项 | 数量 |
|---|---|
| 官方测试程序 | **1 个**：`test/unittest.c` → `unittest` |
| 测试壳脚本 | `test/` 下 8 个 `.sh`（`run_all.sh` / `run_normal.sh` / `run_sanitizer.sh` / `run_valgrind.sh` / `run_gcov.sh` / `run_gprof.sh` / `run_compare.sh` / `clean.sh`），均为**手工驱动脚本**，依赖 gcc/valgrind/gcov/gprof 等宿主工具，非自包含测试 |
| CMake 注册的测试 | 上游 **0 个**（`CMakeLists.txt` 无 `enable_testing()`/`add_test`） |
| 测试数据 | `test/territories.csv`（534 个物理行 = 1 行表头 + 533 条数据行，编号 0–532；上游自报 `533 lines tested`）、`test/alphabets.csv` |
| `unittest.c` 内部测试函数 | **19 个**：`main()` 依次调用 19 个 `test*()` 函数，运行时归入 **12 个**打印分组（Environment / Robustness / Alphabet / Alphabet per territory / Parser / Territory name / Territory / Distance / Mapcode format / Encode-decode / Re-encode / Bug-fix regression） |

> 19 与 12 的对应关系（每组内的函数数）：Environment 1、Robustness 1、Alphabet 2、
> Alphabet per territory 1、Parser 1、Territory name 1、Territory 4、Distance 1、
> Mapcode format 2、Encode/decode 3、Re-encode 1、Bug-fix regression 1 = **19**。
> 另有 3 个辅助函数（`testEncodeRobustness` / `testDecodeRobustness` /
> `testGetTerritoryCode`）由其他测试函数内部调用，归属其所在分组，不单独计为用例。
> 这两个数字都由主配方 `build()` 在每次构建时**实测并校验**，不是文字声明（见 5.2）。

结论：上游测试的**权威入口是单个 `unittest` 可执行文件**（`test/README.md` 与
`run_normal.sh` 均如此），故适配把它注册为 CTest 目标并在 `build()` 中真实执行。

### 5.2 实测执行

| 环境 | 执行方式 | 结果 |
|---|---|---|
| 本地 WSL（x86_64 交叉编译） | `qemu-aarch64 unittest`（显式） | **upstream test groups: 12/12 reported, 19/19 test functions invoked by main()**；**Executed 245633397 tests, found 0 errors → Unit tests passed**，约 200 s |
| 消费者测试 | `qemu-aarch64 test_mapcode` | **24 checks, 0 failures** |
| 命令行工具 | `qemu-aarch64 bin/mapcode -e/-d` | 往返 `NLD 2Z.4Y → 52.37021400000123 4.895134375` |
| CI（aarch64 OpenHarmony 原生） | 直接执行 | 见本 MR 最近一次 CI 构建（构建包 `archives/m/mapcode/2.5.7`） |

**用例数是构建时实测的，不是文字声明。** 主配方 `build()` 把 `unittest` 的输出
重定向到 `upstream_unittest.log` 后逐项校验，任一条不满足即 `ConanException` 让
`conan create` 失败：

| 校验项 | 判据 | 不满足时 |
|---|---|---|
| 12 个分组标题 | 12 个 section 标题必须全部出现在输出里（证明 `main()` 每组都真跑了，而不是提前退出） | `upstream unit test did not report these groups: [...]` |
| 19 个测试函数 | 从取到的 `test/unittest.c` 统计 `main()` 内 `nrTests += test*();` 调用点，必须 == 19 | `upstream main() invokes N test functions, expected 19; the suite changed shape` |
| 汇总行 | 必须匹配 `Executed <n> tests, found <m> errors` | `produced no 'Executed ... found ... errors' summary` |
| 错误数 | `m == 0` 且输出含 `Unit tests passed` | `upstream unit test reported <m> errors` |

通过后按分组逐条打印证据（`[upstream] Environment tests` … `[upstream] Bug-fix
regression tests`）并输出 `19/19` 与断言总数，使 CI 日志本身即可核验用例数。

> **反向验证（证明该门禁不是空壳）**：把 `_UPSTREAM_TEST_FUNCTIONS` 临时改成 20
> 后重跑，构建按预期失败：
> `ConanException: upstream main() invokes 19 test functions, expected 20; the suite changed shape`，
> `conan create` 退出码 1。验证后已还原为 19。

上游 `Robustness tests` 段有 2 条 `*** WARNING ***`（`lat=±inf` 时
`encodeLatLonToMapcodes` 返回 0）。这是**上游自身的健壮性告警**，
不计入 error 计数、不影响退出码，在 x86_64 上同样复现，**与平台无关，故不修改**。

### 5.3 上游测试用例修改说明

**未修改任何上游测试用例**。`test/unittest.c`、`territories.csv`、`alphabets.csv`
逐字来自上游 v2.5.7 tarball，补丁只在 `CMakeLists.txt` 中新增 CTest 注册
（`add_test` + `WORKING_DIRECTORY`），不触碰测试源码与数据。

## 6. 补全的测试用例

| 用例 | 位置 | 说明 |
|---|---|---|
| 库 API 消费者测试（24 断言） | `test_package/test_mapcode.c` | 版本常量与导出变量一致性、`getTerritoryCode`/`getTerritoryIsoName` 往返与非法码拒绝、编码、格式校验（正/反例）、解码误差上界、2 位精度字符使误差严格下降、`encodeLatLonToMapcodes` 计数一致性、`distanceInMeters` 零距离、`maxErrorInMeters` 与实测误差一致性、无 territory 上下文编码 |
| 命令行工具端到端 | `test_package/conanfile.py::test()` | 真实执行打包产物 `bin/mapcode`：`-e 52.3702 4.8952 NLD` 断言输出非空且全部带 `NLD ` 前缀，解析出 mapcode 后 `-d NLD <mapcode>` 断言经纬回落在 0.05° 内 |
| 上游官方测试接入 | 主配方 `build()` | 19 个上游测试函数（12 个分组）共 245633397 条断言纳入 `conan create` 强制门禁，且分组/函数数在每次构建时实测校验 |

> 鸿蒙特有测试：命令行工具往返用例依赖 aarch64 OpenHarmony 产物实际执行
> （本机经 `qemu-aarch64`），满足"鸿蒙特有测试 ≥ 1"。

## 7. 门禁实测结果

| 门禁 | 结果 | 依据 |
|---|---|---|
| L0（a–q 结构/配方/依赖/分支/URL/settings） | **pass** | L0a–L0e 结构齐全；L0i 无外部依赖；L0j 版本未占用；L0k `commands.json` 校验通过（`type=tool`/`name`/`versions`）；L0n 分支 `feat/mapcode-2.5.7` 匹配；L0p settings 四项齐全；L0q `exports_sources` 含 patches |
| KC（知识库质量） | **pass** | 540 正式条目一致；草稿写在 `knowledge/drafts/`，不污染 `knowledge/graph/E*.kv` |
| JC（垃圾文件） | **pass** | 分支有提交后 `git diff origin/main...HEAD` 只含本包文件（JC 全量扫描会命中 `cloog`/`kics` 的**存量**脏文件，与本 PR 无关） |
| L1（测试真实执行） | **pass** | L1a `Launching test_package` 命中；L1b 编译/运行痕迹存在；L1d 无 echo/print 空壳；**L1e 破坏性反向验证通过**——实测 `[sabotage] bin/ lib/ include/ moved away` 后 `conan test` 非零退出，证明测试真依赖被测包。<br>注：L1c 显示 `[ok]` 属**字符串巧合命中**——其正则 `make.*check\|ctest` 匹配到的是补丁**文件名** `0001-cmake-relocatable-install-libm-fallback-and-ctest.patch` 与补丁描述里的 "CTest" 一词（构建日志第 8、67 行），并非真的执行了 `ctest`。上游测试的真实执行是 `RUN: ".../unittest"`（日志第 117 行），`upstream test groups: 12/12 ... 19/19` 与 `Executed 245633397 tests, found 0 errors` 紧随其后（第 131–132 行）。L1c 本身为 `[step]` 提示级，不影响判定；上游测试覆盖由主配方 `build()` 的硬门禁保证，不依赖 L1c。 |
| L2（冒烟） | **skip（非阻断）** | 上游 `mapcode --version` / `--help` 打印用法后 `return NORMAL_ERROR`（退出码 1），两项都不满足 → `L2_RESULT=skip: mapcode version/help failed`。属上游既有行为，**不裁剪、不改上游语义**；门禁代码中该分支为 `[warn] ... (non-blocking)`，不计入失败 |
| L4（安全扫描） | **pass** | 补丁无危险函数；产物静态链接 |
| L5（产物基线/SONAME） | **pass** | `lib/`+`bin/`+`include/` 均有内容；产物为静态库与静态可执行文件，无 `.so`，不触发 SONAME 门禁；无系统同名 `.so` 冲突 |

## 8. 配方要点速查

- `settings`：`os/compiler/build_type/arch` 四项齐全。
- R32：`if self.settings.os in ("Linux", "OHOS")`。
- E092：`CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（Conan `arch=armv8` ↔ CMake `aarch64`）。
- R33：`build()` 不裸用 `${CC}`/`${CFLAGS}`，编译器与工具链全部由 `CMakeToolchain` 从
  `tools.build:compiler_executables` conf 注入。
- R38：产物含可执行文件 → 软件级 `archives/m/mapcode/commands.json`（`type=tool`），
  且 `package_info()` 显式声明 `bindirs = ["bin"]`（否则 PF8 会按"纯库包"判定并拦 commands.json）。
- R37：首次适配用上游版本号 `2.5.7`，无适配修复后缀。
- R39：源码 URL 为 GitHub 官方 tag 归档地址（`PF7` 官方托管例外），sha256 已校验。
- R49/E524：无依赖注入需求，未触碰共享 `/usr/local`。
- 补丁零平台宏（PF5 合规），无 `__OHOS__` 注入、无 `replace()` 动态注入。

## 9. 复现命令

```bash
# W3 本地编译验证（硬门槛）
conan create archives/m/mapcode/2.5.7 --name=mapcode --version=2.5.7 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing

# CI 同源门禁
CI_PACKAGES="archives/m/mapcode/2.5.7" CONAN_PROFILE=ohos-aarch64-wsl \
  zsh ci/conan/build_and_test.sh
```
