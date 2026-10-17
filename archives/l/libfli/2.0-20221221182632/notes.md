# libfli 2.0-20221221182632 适配笔记

## 任务与结论

| 项 | 值 |
|---|---|
| 库 | libfli（Finger Lakes Instrument 相机/调焦轮控制库） |
| 上游 | https://github.com/indilib/indi-3rdparty 的 `libfli/` 子目录 |
| 上游版本 | 2.0+20221221182632（conan 规范化为 `2.0-20221221182632`） |
| 分支 | `feat/libfli-2.0-20221221182632` |
| 状态 | built（W3 本地 conan create 通过 + CI 同源门禁全绿，6 个消费者用例 / 71 项检查；远端 CI 修复见「远端 CI 差异」） |
| 制品 | `libfli.a` + `include/libfli.h` + `lib/udev/rules.d/99-fli.rules` + `licenses/LICENSE.BSD`（默认 `shared=False`，实测包内**只有** `libfli.a`，无 `libfli.so.2`） |

## 远端 CI 差异：cmake_minimum_required 与 CMake 4.x

**远端 CI（构建 #63817，worker OpenHarmonyPCDeveloper-CI-018）在 configure 阶段失败于本机未能复现的一步**：

```
CMake Error at CMakeLists.txt:1 (cmake_minimum_required):
  Compatibility with CMake < 3.5 has been removed from CMake.
  ...
  Or, add -DCMAKE_POLICY_VERSION_MINIMUM=3.5 to try configuring anyway.
```

上游 `CMakeLists.txt:1` 是 `cmake_minimum_required(VERSION 3.0)`。**CMake >= 4.0 移除了
对 `< 3.5` 的兼容支持**，遇到 `VERSION 3.0` 直接硬报错，任何项目逻辑都还没跑到。

本机 WSL 的 CMake 是 3.22.1（对 3.0 只告警不报错），CI worker 上是 CMake 4.x —— 这正是
「W3 本地全绿、远端红灯」的原因。这是**工具链版本差异**而非配方逻辑错误，且与 OHOS 无关
（任何装了 CMake 4 的机器上都会失败）。

### 关键坑：必须用真正的 `-D`，不能用 `tc.variables`

第一次修复（commit `656e3a4c`）把它写进了 toolchain：

```python
tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"   # 无效！
```

CI #63837 证明这**完全没生效** —— 日志里的 cmake 命令行里根本没有这个 `-D`，报错一字不变。
原因：`CMakeToolchain.variables` 会被写进 `conan_toolchain.cmake`，而 CMake 是在自己的
**内部 "system" scope** 里加载 toolchain 文件的；在那里 `set()` 出来的**普通变量不会传递到
项目的目录作用域**，所以 `cmake_minimum_required()` 读到的仍是空值。

正确做法是走命令行 `-D`（生成 cache entry，能跨作用域存活），也正是 CMake 报错信息本身
推荐的形式：

```python
cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
```

> 若一定要走 toolchain，需用 `tc.cache_variables[...]`（写 `CACHE` 条目）而不是
> `tc.variables[...]`（普通变量）。命令行 `cli_args` 最直白，且会原样出现在 CI 日志里便于核对。

## 制品缺陷：libfli.a 非 PIC，下游 .so 无法吸收（本轮修复）

评审要求补鸿蒙特有消费者用例时，为了能断言「包内制品在 OHOS 动态加载链路里真的可用」，
对包内 `lib/libfli.a` 做了下游 `.so` 吸收实验，暴露出一个**真实的打包缺陷**：

```
$ clang -shared -o probe.so -Wl,--whole-archive libfli.a -Wl,--no-whole-archive \
      -Wl,-rpath,<libusb lib> -L<libusb lib> -lusb-1.0 -lm -lpthread
ld.lld-15: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol
'devices'; recompile with -fPIC
>>> defined in libfli.a(libfli.c.o)
>>> referenced by libfli.c
>>>               libfli.c.o:(FLIStartVideoMode) in archive libfli.a
ld.lld-15: error: relocation R_AARCH64_ADD_ABS_LO12_NC cannot be used against symbol
'devices'; recompile with -fPIC
（共 20 条同类错误）
```

**根因**：CMake 对 static target **默认关闭** `POSITION_INDEPENDENT_CODE`，而 libfli 的
`devices[]`/`DEVICE` 是文件级全局量（非 PIC 编译下走 `ADR_PREL_PG_HI21` 直接寻址）。
在 OHOS/aarch64 上，静态库几乎总是被下游 `.so` 吸收（NDK 生态的硬性要求），
所以默认产出的 `libfli.a` 对目标平台的主要消费方式不可用。

**修复**：`generate()` 里加 `tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"`。
不碰任何上游源码，只影响编译期 `-fPIC`；`libfli.a` 体积 184826 B → 184834 B（+8 B）。
`shared=True` 路径本就是 PIC，不受影响。

**受控负向验证**（不是口头断言，是同机同命令的正反对照）：从包内真实归档里取出
`libfli.c.o`，用同一工具链 `-fno-pic` 重编后替换回归档成员，再跑 HC-6.c 用的同一条命令：

```
############ NEG: downstream .so link of the -fno-pic archive ############
NEG exit=1
ld.lld-15: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'devices' ...
NEG linker errors: 20
############ POS: the packaged archive, same command ############
POS exit=0; exported FLI* = 73
```

即：**非 PIC 归档连下游 `.so` 都编不出来，HC-6.c 根本走不到断言**；修复后同命令成功并
导出 73 个 `FLI*` 符号。这条负向对照同时也是 rule12「禁止空壳」的反向证据。

> 顺带修正一处在 `manifest.yaml` 里的**不实声明**：原 `artifacts` 列了
> `lib/libfli.so -> libfli.so.2` 与 `lib/libfli.so.2 -> libfli.so.2.0`。默认
> `shared=False` 下 `cmake.install()` 只装 `libfli.a`（实测包内文件清单见下），
> `.so` 只在 `-o shared=True` 时才出现。已按实测改正。

## W0 依赖发布检查（R35：用 conan download 判定，禁用 conan list）

```
conan download "libusb/1.0.27"   -r=ohpcd --only-recipe   → rc=0  rev 0e6a7c47e7b3b5c1
conan download "libindi/2.2.2.1" -r=ohpcd --only-recipe   → rc=0  rev 9847189a336645af
```

两个依赖均已发布；`conan install --requires=libusb/1.0.27 --requires=libindi/2.2.2.1
-pr:h=ohos-aarch64-wsl` 能拉到 OHOS aarch64 binary（libindi 传递拉取
cfitsio/gsl/libnova/curl/fftw/zlib/libjpeg/libev，全部命中缓存）。**无需先适配依赖。**

## W0b 历史经验核验 + CI 能力矩阵

- `archives/l/libfli/` **无历史归档**，无 notes.md 需核验。
- CI 能力矩阵：libfli 是 **C + CMake**，落在 `gcc/clang/make/cmake/ninja ✅` 一档，
  不涉及 Rust/OCaml 等缺工具链语言 → 立项成立。
- 姊妹包 `libindi/2.2.2.1`、`libfishcamp/1.2` 为同 monorepo 兄弟包且已绿，
  对齐其结构。

## 版本号与源码来源

上游 indi-3rdparty 是 monorepo，**没有为 libfli 单独打 tag**。Debian Astronomy Team
以 `orig.tar.gz` 发布该子目录快照，版本号 `2.0+20221221182632`，其中时间戳
`20221221182632` 即对应 git 提交时刻（2022-12-21 18:26:32），与任务给定版本号一一
对应，是该版本的**权威可下载源**（R39）。

- sha256：`41d1bf856f43c860c033285559f4081a780a3b8525dd4c7eebfee67d9f42711c`（134270 B）
- URL 里的 `+` **故意写成字面量而非 `%2B`**：CI 的 pre-download 步骤会把源码 URL
  改写成 `file://` 本地路径，Conan 随后对 `file://` 路径做百分号解码。若 URL 写成
  `%2B`，磁盘上的缓存文件名保留 `%2B`、Conan 却按解码后的 `+` 去查 → `FileNotFoundError`。
  两种写法在 deb.debian.org 上均可下载（实测 HTTP 200、字节数与 sha256 完全一致）。

## 探索阶段定位的 3 个真实问题

### 问题 1：FindINDI.cmake 版本正则与 INDI 2.x 不兼容（致命，configure 阶段）

```
CMake Error at cmake_modules/FindINDI.cmake:220 (message):
  failed to detect INDI version
```

2022 快照的正则 `" .*INDI_VERSION ([0-9]+).([0-9]+).([0-9]+)"` 假定宏后直接跟数字，
而 INDI 2.2.2 的 `indiversion.h` 写的是 `#define INDI_VERSION "2.2.2"`（带引号）→ 不匹配。

**这不是 OHOS 特有问题**，Linux 上同样复现。**修复方式（路径 B：回移上游修复）**：
indi-3rdparty master 已修同一行，逐字回移为
`MATCHES "INDI_VERSION[ ]+\"?([0-9]+)\\.([0-9]+)\\.([0-9]+)\"?"`，
diff 实测仅 1 处 hunk（+1/-1）。补丁**不含任何平台宏**，不触发 R8。

### 问题 2：libusb 头文件路径（Conan 布局下致命）

```
unix/libusb/libfli-usb-sys.c:46:10: fatal error: 'libusb-1.0/libusb.h' file not found
```

上游 `CMakeLists.txt` 调了 `find_package(USB1 REQUIRED)`、`include_directories(${INDI_INCLUDE_DIR})`，
**唯独没把 `USB1_INCLUDE_DIRS` 加进 include 路径**——源码写的是带版本目录前缀的
`<libusb-1.0/libusb.h>`，distro 装到 `/usr/include/libusb-1.0/` 靠系统默认路径解析。
Conan 包保持同样布局，但 `include/` 根目录不在默认搜索路径里。

**修复**：`generate()` 里注入 libusb 的 include **根目录**。两个陷阱：
① 写成 `-I"path"`（shell 习惯）会被 Conan 生成的 `string(APPEND CONAN_C_FLAGS " -I"path"")`
   提前截断，flag 静默失效（只有一条 CMake dev warning）；
② 改用 `tc.variables["CMAKE_INCLUDE_PATH"] = path` 会**覆盖** toolchain 生成的
   `list(PREPEND CMAKE_INCLUDE_PATH ...)` 列表，把 libindi 的 include 挤掉，
   报错漂移成 `Could not find INDI include directory`。
最终写法：`tc.extra_cflags.append(f"-I{usb_inc}")`（无内层引号，且取根目录）。

### 问题 3：udev rules 装到不可写的绝对路径

上游 `set(UDEVRULES_INSTALL_DIR "/lib/udev/rules.d" CACHE STRING ...)`，CI 沙箱不可写。
**修复**：`UDEVRULES_INSTALL_DIR=lib/udev/rules.d`（相对 `CMAKE_INSTALL_PREFIX`），
rules 文件仍安装（实测产物 `lib/udev/rules.d/99-fli.rules`，与上游字节一致），
只是进包内私有 prefix（R49：不注入共享系统前缀）。

## 补丁清单

| 补丁 | 类型 | 平台宏 | 说明 |
|---|---|---|---|
| `0001-FindINDI.cmake.patch` | portability | **无** | 回移上游 indi-3rdparty master 的 `INDI_VERSION` 正则修复，兼容 INDI 2.x 带引号版本宏。与平台无关（Linux 同样需要）。 |
| `0002-CMakeLists.txt.patch` | portability | **无** | `ADD_LIBRARY` 不再硬编码 `SHARED`，改为遵循标准 `BUILD_SHARED_LIBS` 开关（未定义时保持原 shared-only 行为），使打包器可请求静态库。 |

`patches/` 目录实测 `__OHOS__`/`OHOS` 关键词 **0 命中**。

## 配方关键决策

| 决策 | 取值 | 理由 |
|---|---|---|
| CMAKE_POLICY_VERSION_MINIMUM | `3.5`（经 `cli_args` 传 `-D`） | CMake >= 4.0 移除 `< 3.5` 兼容；见「远端 CI 差异」 |
| CMAKE_POSITION_INDEPENDENT_CODE | `ON` | 静态库必须 PIC 才能被下游 `.so` 吸收；见「制品缺陷」 |
| CMAKE_SYSTEM_NAME | `Linux` | E092，CMake 不认 HarmonyOS；同 libindi/2.2.2.1 |
| CMAKE_SYSTEM_PROCESSOR | `aarch64` | 与工具链 shim 的 `aarch64-linux-ohos` 对齐 |
| CMAKE_FIND_PACKAGE_PREFER_CONFIG | `OFF`（toolchain 末尾 Block） | Conan 默认 ON，会 shadow 项目自带 `FindUSB1.cmake`/`FindINDI.cmake` 的旧式变量；同 libindi |
| libusb include | `-I<include 根>`（无引号） | 见问题 2 |
| UDEVRULES_INSTALL_DIR | `lib/udev/rules.d` | 见问题 3 |
| shared 选项 | 默认 False | R26；`shared=True` 仍可产出真实 `libfli.so.2`（补丁 0002 保证） |
| settings.os 判断 | `not in ("Linux","OHOS")` → 抛错 | R32 |
| commands.json | **不需要** | 纯库，无 bin/ 产物；CI L0k 实测「library package, commands.json not required」 |
| build() 变量来源 | 全部来自 `self.conf` / Conan Toolchain | R33：build() 内零裸用 `${CC}`/`${CFLAGS}` |

### 依赖声明说明

上游 `CMakeLists.txt` 有 `find_package(USB1 REQUIRED)` 和 `find_package(INDI REQUIRED)`，
但**只把 `INDI_INCLUDE_DIR` 加进 include 路径，从未链接任何 INDI 库**
（`TARGET_LINK_LIBRARIES(fli ${USB1_LIBRARIES} -lm -lpthread)`）。

libfli 只需 INDI 的**头文件**（`libfli.c` / `libfli-camera-usb.c` include 了
`indimacros.h`，用其中的 `INDI_UNUSED` 宏）。仍声明 `libindi` 为 requirement：
① 与上游声明一致；② 让下游拿到一致 include 路径；③ `FindINDI.cmake REQUIRED` 本就需要它存在。

> 姊妹包 `libfishcamp/1.2` 走的是「本地 `#define INDI_UNUSED(x)` 彻底摘掉 INDI」路线。
> libfli 保留上游 `find_package(INDI REQUIRED)` + 回移上游正则修复——因为 libfli 自带
> `FindINDI.cmake`，用它更贴近上游构建语义，且 libindi 已在制品仓中。

## 上游测试情况与补全

**上游测试用例数 = 0**：indi-3rdparty 的 libfli 子目录不提供任何自动化测试套件，
CI 也不存在 `make check` / ctest 目标（CI L1c 实测「No upstream make check/ctest in log」）。

### 统计口径：按「具名端到端用例数」，不按断言数

第一版补全把测试写成 T1–T6 六组共 46 条**孤立断言**并按「46」填报。评审 rule12 判其为
「纯断言，不算完整消费者用例」。参照 `feedback/SKILL_FEEDBACK_009f9300.md`（wise 2.4.1 同类
返工：把断言集合重构为 HC-1…HC-7 具名端到端用例，统计口径由「断言数」改为「用例数」），
本轮把整个 `test_package` 重构为 **6 个具名端到端消费者用例**，用例内的 ok/FAIL 行
只是该用例的检查项，不再作为统计口径。

**补全测试用例数 = 6**（`test_package/test_libfli.c`，HC-1…HC-6，71 项检查全过）：

| 用例 | 类型 | 端到端流程 | 检查项 |
|---|---|---|---|
| **HC-1** 版本自描述服务回环 | consumer_e2e | 索取版本横幅 → 在最小缓冲尺寸上复现同一结果 → 走通 EOVERFLOW/EINVAL 降级契约 | 7 |
| **HC-2** 设备清单迭代流程 | consumer_e2e | `FLICreateList` → `FLIListFirst` → `FLIListNext` 直到上游约定的 `-EBADF` 结束信号 → `FLIDeleteList`；连做两轮验证库内全局 `firstdevice/currentdevice` 可重入 | 11 |
| **HC-3** 设备清单落盘与回读 | consumer_e2e | 覆盖 6 个 domain 组合打通 parport/usb/serial 三后端 → 把 `filename;name` 条目写成**真实报告文件** → 回读校验字段结构/行数并与 `FLIList` 返回值对齐 | 18 |
| **HC-4** 诊断子系统端到端 | consumer_e2e | `FLIDEBUG_ALL` → 驱动真实枚举 → `dup2` 捕获进程真实 stderr → 校验带 `libfli:` 前缀且描述本次枚举的诊断行 → 关 debug 重跑校验输出归零 | 5 |
| **HC-5** 设备句柄越界防护 | consumer_e2e | 9 个跨子系统 API 对越界句柄 `-1` 必须经 `CHKDEVICE` 拒绝；`FLIGetModel(NULL)` 拒绝；`FLIOpen` 对不存在的并口地址干净失败 | 11 |
| **HC-6** 鸿蒙特有：包内制品在 OHOS 动态加载链路中的端到端消费 | **harmony_specific** | (a) `__aarch64__` + `uname().machine=aarch64` + LP64（`__OHOS__` 只报告不断言，见下）；(b) 解析**包内** `lib/libfli.a`（GNU/BSD/plain 三种 ar 长名格式）逐成员校验 ELF64/ET_REL/EM_AARCH64；(c) 用**该包内静态库**编出下游 `.so`，`dlopen` + `dlsym` + 跨 `.so` 边界真实调用 + 与静态副本比对横幅 + `dlclose`；(d) 读**包内** `99-fli.rules` 校验 USB 子系统匹配与 FLI 厂商 ID `0f18`，并确认未落进共享系统前缀（R49） | 18 |

HC-2 用的 `FLICreateList/FLIListFirst/FLIListNext/FLIDeleteList` 迭代器 API 第一版完全没覆盖，
是本轮新增的真实调用路径；HC-3 覆盖的三后端分派（`unix_fli_list()` 按 `domain & 0x00ff`）
刻意用**任何环境都成立的不变量**（不崩溃、列表良构、必定可释放、重复调用一致、未定义接口码
被 dispatch 自身以 `EINVAL` 拒绝），而非硬编码某个后端的返回码——否则同一份测试在 CI 与本地
会给出不同结论。

> **为什么 HC-6.a 不断言 `__OHOS__`**：`__OHOS__` 由 **OHOS NDK driver**（CI 上的
> `/data/service/hnp/bin/clang`）预定义，但任何「以 OHOS 为目标的 clang」并不必然定义它——
> 本机的 `/data/service/hnp/bin/clang` → `/opt/ohos-toolchain/clang` 就没有（实测
> `clang -dM -E - | grep -i ohos` 无输出，`__aarch64__` 有）。把它写成硬断言等于在**测工具链
> 而不是测制品**，且会让本地复验与 CI 结论不一致。故 HC-6.a 的硬信号全部换成任何环境都可
> 观测的量：`__aarch64__`（确实是交叉编译、不是编给宿主）、`uname().machine`（确实跑在
> aarch64 内核上）、LP64、以及 HC-6.b 的 `EM_AARCH64` 和 HC-6.c 的平台加载器 `dlopen`。
> `__OHOS__` 只在日志里**如实报告**当前编译器是否预定义。

### 防空壳的结构性保障（R34 / rule12）

- `test_package/conanfile.py` 的 `test()` 用 `self.run` 真实编译并执行；
- **解析用例级结果**：统计 `case HC-n PASS|FAIL` 行，任一用例 FAIL、缺少 `HC-6`、
  完全没有用例行、缺 `RESULT: PASSED`，或两行汇总（`== N cases, M failed ==` /
  `== N checks, M failures ==`）任一非零，均抛 `AssertionError`；
- **缺输入即失败而非跳过**：包内 `libfli.a` 或 `99-fli.rules` 缺失、或没给下游 `.so` 路径，
  直接抛 `AssertionError`（不静默 skip），因此用例无法被「掏空输入」变成空壳。

### L1e 破坏性反向验证（5 项，均实测）

| 编号 | 破坏动作 | 实测结果 |
|---|---|---|
| NEG-A | 用 `-fno-pic` 重编 `libfli.c.o` 顶替包内归档成员 | 下游 `.so` 链接 exit=1，20 条 `R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC` |
| NEG-B1 | 把包内 `libfli.a` 路径指向不存在的目录 | 编译期 `clang: error: no such file or directory: '.../libfli.a'` |
| NEG-B2 | 传入不存在的 `99-fli.rules` | 套件 exit=1，`HC-6.d1/d2/d3` FAIL，`case HC-6 FAIL`、`RESULT: FAILED` |
| NEG-B3 | 不传下游 `.so` 路径（空串） | 套件 exit=1，`HC-6.c1` FAIL，`case HC-6 FAIL` |
| NEG-B4 | 用一行文本顶替 `libfli.a` | 套件 exit=1，`HC-6.b1` FAIL（不是 ar 魔数） |
| POS | 全部制品就位 | exit=0，`== 6 cases, 0 failed ==`、`== 71 checks, 0 failures ==`、`RESULT: PASSED` |

## 验证结果

W3 本地 `conan create`（rc=0）：
- 13 个源文件全部编译（`grep -c 'Building C object'` = 13），含 `unix/linux/libfli-parport.c`
- `[100%] Linking C static library libfli.a`
- 产物（实测包内文件清单）：`include/libfli.h`（与上游**字节一致**）、`lib/libfli.a`（184834 B）、
  `lib/udev/rules.d/99-fli.rules`（与上游**字节一致**）、`licenses/LICENSE.BSD`
- `libfli.a` 导出 73 个 `FLI*` + 67 个 `fli_*` 符号
- `== 6 cases, 0 failed ==` / `== 71 checks, 0 failures ==` / `RESULT: PASSED`
- `[test_libfli] use cases passed=6 failed=0 -> HC-1, HC-2, HC-3, HC-4, HC-5, HC-6`

CI 同源门禁 `ci/conan/build_and_test.sh`（`CI_PACKAGES="archives/l/libfli/2.0-20221221182632"`）：

| 门禁 | 结论 | 关键证据 |
|---|---|---|
| G0 | pass | 知识图谱完整性 541 条 |
| KC | pass | KC1–KC5 全 OK，Errors: 0 |
| JC | pass | Junk Files: 0，JC6 单软件原子性合规 |
| L0 | pass | L0i 两依赖均在 registry；L0j 首次发布；L0k 库类型免 commands.json；L0m 目录结构合法 |
| L1 | pass | L1a test_package 已执行；L1b 有编译/运行证据；L1c 上游无 make check（如实记录） |
| L2 | skip | 纯库无 bin/ 目录 |
| L4 | pass | patches 干净 |
| L5 | pass | lib/ 有内容 |

> **JC 前置说明**：`junk_check.sh` 的 full 模式会扫到 `origin/main` 上**其他包**遗留的
> 运行时状态文件（`archives/c/cloog/0.21.1/.build-closed`、`.staging-verified`、
> `archives/k/kics/2.1.20/.staging-verified`、`archives/t/thc/3.8/.staging-verified`）。
> 已在**纯净的 origin/main worktree**（不含 libfli）上复现同样的 JC1/JC5 失败，
> 确认是 main 分支存量问题、与本 PR 无关；且这 4 个文件属他人归档目录，本任务不触碰。
> 因此按 CI 实际的 `checkout-pr` 流程（`pr.diff` 存在时走 prdiff 模式）执行门禁，
> 得到上表结论。

## 本地执行通道的一个坑（非配方问题）

本机 WSL 用 `/opt/ohos-guest/` 下的**通用 musl** 作 loader，它没有 OHOS musl 的
fortify 助手 `__fd_chk`，而 libfli 的 `libfli-serial.c` 引用了该符号 → 本地执行时
`Error relocating ...: __fd_chk: symbol not found`（rc=127）。

**真实 OHOS sysroot 的 `libc.so` 是导出 `__fd_chk` 的**（实测 `nm -D` 见 `T __fd_chk`），
CI 跑在真 OHOS 环境上不受影响。已按知识库既有条目
`knowledge/drafts/DRAFT-yosys-0.66-ohos-aarch64-local-run-missing-fd-chk.md` 的做法，
给**本地验证通道**注入一个只定义该符号的 aarch64 shim（`QEMU_SET_ENV=LD_PRELOAD=…`
只作用于 guest，不污染宿主 x86 进程）。**配方本身不含任何本地环境假设。**

## 踩坑与注意事项

1. **`asm/param.h` 不在 `/usr/include/asm/`**：`unix/linux/libfli-parport.c` include 了
   `<asm/param.h>`。第一反应是「OHOS 缺头文件要打补丁」，实测 OHOS sysroot 里有
   `usr/include/aarch64-linux-ohos/asm/param.h`，而工具链 shim 已加
   `-isystem "$SYS/usr/include/aarch64-linux-ohos"` → **无需任何补丁**即可编译通过。
   差点多打一个没必要的补丁。
2. **CMP0074 警告**：`cmake_minimum_required(VERSION 3.0)` < 3.12，CMake 会提示
   `INDI_ROOT` 被忽略。改用 `CMAKE_PREFIX_PATH` 传依赖路径即可绕开。
3. **PREFER_CONFIG 默认值**：Conan 的 `CMakeToolchain` 默认把
   `CMAKE_FIND_PACKAGE_PREFER_CONFIG` 设为 `ON`，必须在 toolchain **末尾**用自定义
   Block 强制 `OFF`（前置设置会被覆盖）。
4. **版本号里的 `+`**：上游 `2.0+20221221182632` 的 `+` 不是合法 conan 版本字符，
   规范化为 `-`。目录名、conanfile `version`、制品名三处必须完全一致（CI L0m-5 校验）。
5. **纯 C 却声明了 CXX**：`PROJECT(libfli CXX C)` 但无 C++ 源文件。配方给 OHOS 补
   `c++`/`c++abi` 到 `system_libs` 是防御性做法。
6. **静态库需要显式链 libusb**：默认 `shared=False` 产出 `libfli.a`，而制品仓的 libusb
   只有 `.so`。test_package 链接时须 `-L<libusb lib> -lusb-1.0` 并加 `-Wl,-rpath`，
   否则 `undefined symbol: libusb_init` 等一批符号。HC-6 里的下游 `.so` 同样要 `-Wl,-rpath`，
   否则 `dlopen` 报 `Error loading shared library libusb-1.0.so.0`。
7. **`--whole-archive` 是必需的**：HC-6 的探针 `.so` 不引用任何 `FLI*` 符号，
   普通链接不会从归档里拉取任何成员，`dlsym` 将一无所获。必须
   `-Wl,--whole-archive libfli.a -Wl,--no-whole-archive`。
8. **ar 归档有三种长名格式**：OHOS/LLVM 工具链的 `ar` 为 `.o` 成员生成
   `//` 长名表并把成员名写成 `/<offset>`，解析归档必须同时支持 plain `name/`、
   BSD `#1/<len>` 和 GNU `/<offset>`（HC-6.b 就是靠这个逐成员读 ELF header 的）。

## 复现命令

```bash
# W3 本地编译验证
cd archives/l/libfli/2.0-20221221182632
QEMU_SET_ENV="LD_PRELOAD=$HOME/.ohos/aarch64-musl/lib/libfdchk.so" \
conan create . --name=libfli --version=2.0-20221221182632 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing

# CI 同源门禁（prdiff 模式，对齐 CI checkout-pr 流程）
cd <worktree>
CI_PACKAGES="archives/l/libfli/2.0-20221221182632" zsh ci/conan/build_and_test.sh
```

> 本机 WSL 执行 OHOS aarch64 二进制需要 `QEMU_SET_ENV=LD_PRELOAD=<__fd_chk shim>`，
> 见「本地执行通道的一个坑」。**这只作用于本地验证通道**，配方与 `test_package/`
> 内不含任何 `QEMU_SET_ENV` / `LD_PRELOAD` / 宿主绝对路径假设。
