- **三方库名称**：libfli（Finger Lakes Instrument 相机 / 滤轮 / 调焦器控制库，INDI 3rdparty 子项目）
- **上游版本**：2.0-20221221182632（上游 `2.0+20221221182632`，conan 版本号把 `+` 规范化为 `-`）
- **上游仓库地址**：https://github.com/indilib/indi-3rdparty
- **适配路径**：路径 A（基础适配）— 零上游源码修改，2 个构建系统 portability 补丁 + 配方侧适配
- **使用知识库**：E092（CMake 不识别 HarmonyOS 平台）、E999-draft-8FBE（OHOS libc 符号族）、DRAFT-ohos-fortify-source-defeats-libc-wrap-mock

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | indi-3rdparty 的 `libfli/` 子目录不提供任何自动化测试套件；解包 tarball 实测无 `test/` 目录、无 `check_PROGRAMS` |
| 集成测试 | 0 | 上游 `CMakeLists.txt` 未注册任何 ctest / `make check` 目标 |
| 其他测试 | 0 | CI 门禁 L1c 侧证据：`No upstream make check/ctest in log` |
| **合计** | **0** | 上游零测试。清点方式与证据见「上游测试用例修改说明」 |

上游零测试的原因：libfli 是**硬件控制库**，所有设备入口（`FLIOpen` / `FLIExposeFrame` / `FLIStepMotor` 等）都需要真实的 FLI 相机，仓库未提供 mock 或模拟层。

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试可沿用，本次未伪造上游用例 |
| 集成测试 | 0 | 不变 | 上游无集成测试可沿用 |
| 鸿蒙特有测试 | 6 | 新增 | HC-1…HC-6 六个具名端到端消费者用例，其中 **HC-6 为鸿蒙特有**，断言全部落在包内真实制品上 |
| **合计** | **6** | **+6** | 6/6 通过（71 项检查 0 失败），见下表与「验证结果」 |

**6 个用例均为完整端到端消费者流程**（构造输入 → 真实调用包内制品 → 产出真实结果 → 回读校验），
不是断言清单：

| 用例 | 端到端流程 | 检查项 |
|---|---|---|
| **HC-1** 版本自描述服务回环 | 索取版本横幅 → 在最小缓冲尺寸上复现同一结果 → 走通 EOVERFLOW/EINVAL 降级契约 | 7 |
| **HC-2** 设备清单迭代流程 | `FLICreateList` → `FLIListFirst` → `FLIListNext` 直到上游约定的 `-EBADF` 结束信号 → `FLIDeleteList`；连做两轮验证库内全局状态可重入 | 11 |
| **HC-3** 设备清单落盘与回读 | 覆盖 6 个 domain 组合打通 parport/usb/serial 三后端 → 写成**真实报告文件** → 回读校验字段结构/行数并与 `FLIList` 返回值对齐 | 18 |
| **HC-4** 诊断子系统端到端 | `FLIDEBUG_ALL` → 驱动真实枚举 → `dup2` 捕获进程真实 stderr → 校验带 `libfli:` 前缀且描述本次枚举的诊断行 → 关 debug 重跑校验输出归零 | 5 |
| **HC-5** 设备句柄越界防护 | 9 个跨子系统 API 对越界句柄 `-1` 必须经 `CHKDEVICE` 拒绝；`FLIGetModel(NULL)` 拒绝；`FLIOpen` 对不存在的并口地址干净失败 | 11 |
| **HC-6** 鸿蒙特有：包内制品在 OHOS 动态加载链路中的端到端消费 | (a) `__aarch64__` + `uname().machine=aarch64` + LP64；(b) 解析**包内** `lib/libfli.a`（GNU/BSD/plain 三种 ar 长名格式）逐成员校验 ELF64/ET_REL/EM_AARCH64；(c) 用**该包内静态库**编出下游 `.so`，`dlopen` + `dlsym` + 跨 `.so` 边界真实调用 + 与静态副本比对横幅 + `dlclose`；(d) 读**包内** `99-fli.rules` 校验 USB 子系统匹配与 FLI 厂商 ID `0f18`，并确认未落进共享系统前缀 | 18 |

> HC-2 使用的 `FLICreateList/FLIListFirst/FLIListNext/FLIDeleteList` 迭代器 API 是本次新增覆盖的上游公开接口；
> HC-3/HC-4 的断言全部是**任何环境都成立的不变量**（不崩溃、列表良构、必定可释放、重复调用一致、
> 未定义接口码被 dispatch 自身以 `EINVAL` 拒绝），不硬编码某个硬件后端的返回码，因此本地与 CI 结论一致。

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> **说明**：上游测试用例数为 0，不存在可被修改的上游测试，本次亦未新增/删除任何上游测试文件。
>
> **上游零测试的清点证据**（不是推断）：解包
> `libfli_2.0+20221221182632.orig.tar.gz`（134270 B，sha256 `41d1bf85…2711c`）后，
> `libfli/` 子目录共 115 个文件，无 `test/`、无 `tests/`、无 `*test*`；
> `CMakeLists.txt` 无 `enable_testing()` / `add_test()` / `check_PROGRAMS`；
> CI 同源门禁 L1c 实测 `No upstream make check/ctest in log`。
>
> **上游源码零修改的核验**：13 个编译单元与上游 `fli_LIB_SRCS` 全集**完全一致**（无增删、无裁剪，
> BSD/OSX 变体按平台条件不参与编译，与上游逻辑一致）；安装的 `libfli.h` 与 `99-fli.rules`
> 与上游 tarball 内同名文件**字节一致**（`patches/` 之外零源码改动）。
>
> 仅有两处构建系统层面的补丁，均不触碰库的业务逻辑，且**均不含平台宏**
> （故不适用 R8 平台宏约束）：

| 补丁 | 类型 | 平台宏 | 内容与理由 |
|---|---|---|---|
| `patches/0001-FindINDI.cmake.patch` | portability | **无** | 2022 快照的 `FindINDI.cmake` 用无引号正则解析版本，INDI ≥ 2.0 的 `indiversion.h` 写成 `#define INDI_VERSION "2.2.2"`（带引号）→ configure 阶段 `FATAL_ERROR: failed to detect INDI version`。**逐字回移上游 indi-3rdparty master 的同一行修复**（diff 实测仅 1 处 hunk，+1/-1）。该缺陷**与平台无关**（Linux 上链接 INDI 2.x 同样复现），故用回移而非平台宏绕过。 |
| `patches/0002-CMakeLists.txt.patch` | portability | **无** | `ADD_LIBRARY(fli SHARED …)` 硬编码共享库，打包器无法请求静态构建。改为遵循标准 `BUILD_SHARED_LIBS` 开关；当该变量**未定义**时保持原有 shared-only 行为，故上游原生构建完全不受影响。 |

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为 libfli **无硬件依赖的公开 API 表面**补全 6 个具名端到端消费者用例
>   （HC-1…HC-6，71 项检查），覆盖：版本自描述、**设备清单迭代器 API**（`FLICreateList` 系列，
>   本次新增覆盖）、跨全部接口后端的设备枚举与报告落盘、诊断子系统、句柄越界防护、
>   以及包内制品在 OHOS 动态加载链路中的消费。
> - **补全原因**：上游是硬件控制库，无自动化测试套件（见上），
>   若只做纯断言则无法证明产物在 OHOS 上真的可用（rule12 判为「纯断言」）。
>   因此按**用例数**而非断言数组织，并新增 1 个鸿蒙特有端到端用例 HC-6。
> - **新增测试文件清单**：
>   1. `test_package/test_libfli.c` — 6 个具名端到端消费者用例的实现（含 ar 归档解析、ELF 校验、dlopen/dlsym 跨 `.so` 边界调用）
>   2. `test_package/conanfile.py` — 真实编译 + 执行；额外编译下游 `.so` 探针；解析**用例级**结果并在任一用例 FAIL / 缺 HC-6 / 缺任一包内制品时抛 `AssertionError`
>   3. `test_package/MANIFEST.yml` — 申报 6 个用例与逐例检查项数
> - **防空壳的结构性保障**：缺包内 `libfli.a` / `99-fli.rules` / 下游 `.so` 任一输入时**直接抛错而非跳过**，
>   所以用例无法被「掏空输入」退化成空壳；CI 自身的 L1d/L1e 门禁也通过
>   （`L1e: Negative test confirmed — test genuinely depends on libfli`）。

## 验证结果

- 编译状态：**通过**（rc=0）
- 上游测试用例通过率：**不适用**（上游测试用例数 N=0，不存在可执行的上游测试；清点证据见上，非虚报）
- 新增测试用例通过率：**6/6 = 100%**（71 项检查 0 失败）

### 验证证据

#### 本地 `conan create`（rc=0，HarmonyOS PC / OpenHarmony aarch64，clang 15 + libc++）

```
== 6 cases, 0 failed ==
== 71 checks, 0 failures ==
RESULT: PASSED
[test_libfli] use cases passed=6 failed=0 -> HC-1, HC-2, HC-3, HC-4, HC-5, HC-6
[test_libfli] checks passed=71 failed=0
       .so round-trip: "Software Development Library for Linux 1.999.1" (both copies agree)
       /root/.conan2/p/b/<pkg>/p/lib/libfli.a: 15 header(s), 13 object(s), 13 relocatable, 13 aarch64
       stderr capture: debug on = 132 byte(s), debug off = 0 byte(s)
```

- 13 个源文件全部编译（`[100%] Linking C static library libfli.a`）
- 目标平台设置：`os=OHOS os.version=6.0 arch=armv8 compiler=clang 15 libcxx=libc++ build_type=Release`

#### CI 同源门禁 `ci/conan/build_and_test.sh`（`CI_PACKAGES="archives/l/libfli/2.0-20221221182632"`，退出码 0）

| 门禁 | 结论 | 关键证据 |
|---|---|---|
| G0 | pass | 知识图谱完整性检查通过 |
| KC | pass | KC1–KC5 全 OK，`Errors: 0` |
| JC | pass | `Junk Files: 0`，JC6 单软件原子性合规 |
| L0 | pass | L0i 两依赖均在 registry；L0j 首次发布无版本冲突；L0k 纯库免 `commands.json`；L0m 目录结构合法 |
| L1 | pass | L1a test_package 已执行；L1b 有编译/运行证据；L1c 如实记录上游无 `make check`；L1d 非空壳；L1e 破坏性反向测试通过 |
| L2 | skip | 纯库无 `bin/` 目录 |
| L4 | pass | patches 干净（无危险函数） |
| L5 | pass | `lib/` 有内容 |

```
Success: 1   Failed: 0   Pass rate: 100.0% (1/1)
```

#### 负向反向验证（证明用例真的依赖包内制品，不是自说自话）

| 编号 | 破坏动作 | 实测结果 |
|---|---|---|
| NEG-A | 用 `-fno-pic` 重编 `libfli.c.o` 顶替包内归档成员 | 下游 `.so` 链接 exit=1，20 条 `R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC` |
| NEG-B1 | 把包内 `libfli.a` 路径指向不存在的目录 | 编译期 `clang: error: no such file or directory: '.../libfli.a'` |
| NEG-B2 | 传入不存在的 `99-fli.rules` | 套件 exit=1，`HC-6.d1/d2/d3` FAIL，`RESULT: FAILED` |
| NEG-B3 | 不传下游 `.so` 路径 | 套件 exit=1，`HC-6.c1` FAIL，`RESULT: FAILED` |
| NEG-B4 | 用一行文本顶替 `libfli.a` | 套件 exit=1，`HC-6.b1` FAIL（不是 ar 魔数） |
| POS | 全部制品就位 | exit=0，`== 6 cases, 0 failed ==`、`RESULT: PASSED` |

#### 本轮修复的制品缺陷：libfli.a 非 PIC，下游 .so 无法吸收

补 HC-6 时对包内 `libfli.a` 做下游 `.so` 吸收实验，暴露出真实打包缺陷：

```
ld.lld-15: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol
'devices'; recompile with -fPIC
>>> defined in libfli.a(libfli.c.o)
```

**根因**：CMake 对 static target **默认关闭** `POSITION_INDEPENDENT_CODE`，而 libfli 的
`devices[]` / `DEVICE` 是文件级全局量（非 PIC 下走 `ADR_PREL_PG_HI21` 直接寻址）。
在 OHOS/aarch64 上静态库几乎总被下游 `.so` 吸收（NDK 生态硬性要求），因此默认产出的
`libfli.a` 对目标平台的主要消费方式不可用。

**修复**：`generate()` 增加 `CMAKE_POSITION_INDEPENDENT_CODE=ON`，不碰任何上游源码，
只影响编译期 `-fPIC`；`libfli.a` 体积 184826 B → 184834 B（+8 B）。`shared=True` 本就是 PIC，不受影响。
修复后同一条下游 `.so` 命令成功并导出 73 个 `FLI*` 符号（见 NEG-A 的正反对照）。

### 产物

| 文件 | 说明 |
|---|---|
| `include/libfli.h` | 公开头文件，与上游字节一致 |
| `lib/libfli.a` | 静态库（PIC），导出 73 个 `FLI*` + 67 个 `fli_*` 符号 |
| `lib/udev/rules.d/99-fli.rules` | FLI 设备 udev 规则（厂商 ID `0f18`），与上游字节一致，装在包内私有 prefix（R49） |
| `licenses/LICENSE.BSD` | BSD-3-Clause 授权文件 |

> 配方默认 `shared=False`（R26），实测包内**只有** `libfli.a`；`shared=True` 时产出真实
> `libfli.so.2`（SOVERSION 2 / VERSION 2.0，由 `patches/0002-CMakeLists.txt.patch` 保证）。

## 补充说明

### 版本号与源码来源说明

上游 indi-3rdparty 是 monorepo，**未为 libfli 单独打 tag**。Debian Astronomy Team 以
`orig.tar.gz` 形式发布该子目录快照，版本号 `2.0+20221221182632`，其中时间戳
`20221221182632` 即对应 git 提交时刻（2022-12-21 18:26:32），与本任务版本号一一对应，
是该版本的**权威可下载源**（R39）。

- 源码 URL：`https://deb.debian.org/debian/pool/main/libf/libfli/libfli_2.0+20221221182632.orig.tar.gz`
- sha256：`41d1bf856f43c860c033285559f4081a780a3b8525dd4c7eebfee67d9f42711c`（134270 字节，与申报值实测一致）
- 目录名 / `conanfile.py` 的 `version` / 制品名三处一致（CI L0m-5 校验通过）
- URL 里的 `+` **故意写成字面量而非 `%2B`**：CI 的 pre-download 会把源码 URL 改写成 `file://` 本地路径，
  Conan 随后对 `file://` 路径做百分号解码。若写成 `%2B`，磁盘缓存文件名保留 `%2B`、Conan 却按解码后的
  `+` 去查 → `FileNotFoundError`。两种写法在 deb.debian.org 上均可下载（实测 HTTP 200、字节数与 sha256 一致）。

### 依赖

| 依赖 | 版本 | 制品仓状态 | 用途 |
|---|---|---|---|
| libusb | 1.0.27 | 已发布 | `find_package(USB1 REQUIRED)`，USB 传输后端 |
| libindi | 2.2.2.1 | 已发布 | `find_package(INDI REQUIRED)`，提供 `indimacros.h` |

libfli 只使用 INDI 的**头文件**（`libfli.c` / `libfli-camera-usb.c` include `indimacros.h`
使用 `INDI_UNUSED` 宏），上游 `CMakeLists.txt` 从未链接任何 INDI 库；仍声明为 requirement，
与上游 `find_package(INDI REQUIRED)` 保持一致，并让下游拿到一致的 include 路径。

### 关键适配点

| 项 | 取值 | 理由 |
|---|---|---|
| `CMAKE_SYSTEM_NAME` | `Linux` | E092：CMake 不识别 HarmonyOS 平台（姊妹包 libindi/2.2.2.1 同款） |
| `CMAKE_SYSTEM_PROCESSOR` | `aarch64` | 与工具链 triplet `aarch64-linux-ohos` 对齐 |
| `CMAKE_FIND_PACKAGE_PREFER_CONFIG` | `OFF`（toolchain **末尾** Block） | Conan `CMakeToolchain` 默认设为 `ON`，会 shadow 项目自带的 `FindUSB1.cmake` / `FindINDI.cmake` 旧式变量；前置设置会被覆盖，必须末尾强制 |
| `CMAKE_POSITION_INDEPENDENT_CODE` | `ON` | 静态库必须 PIC 才能被下游 `.so` 吸收（见「验证结果」） |
| `CMAKE_POLICY_VERSION_MINIMUM` | `3.5`（经 `cli_args` 传 `-D`） | 上游 `cmake_minimum_required(VERSION 3.0)`，CMake ≥ 4.0 移除 `< 3.5` 兼容会硬报错。**必须走命令行 `-D`（生成 cache entry），写进 `conan_toolchain.cmake` 的普通变量不跨 CMake 内部 system scope 存活**（实测 CI 上 tc.variables 方案完全无效） |
| libusb include | `-I<include 根>`（**无引号**） | 上游 `CMakeLists.txt` 从不把 `USB1_INCLUDE_DIRS` 加进 include 路径（依赖系统 `/usr/include`），Conan 布局下 `<libusb-1.0/libusb.h>` 找不到 |
| `UDEVRULES_INSTALL_DIR` | `lib/udev/rules.d` | 上游默认绝对路径 `/lib/udev/rules.d` 在 CI 沙箱不可写；改为相对 `CMAKE_INSTALL_PREFIX`，rules 文件仍安装（R49：不注入共享系统前缀） |
| 源码 URL 中的 `+` | 字面量而非 `%2B` | 见「版本号与源码来源说明」 |

### 两个环境事实（**非配方缺陷**，供评审参考）

1. **JC 门禁在 full 模式下的存量红灯**：`junk_check.sh` 的 full 模式会扫到 `origin/main`
   上**其他包**遗留的 4 个运行时状态文件（`archives/c/cloog/0.21.1/.build-closed`、
   `archives/c/cloog/0.21.1/.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`、
   `archives/t/thc/3.8/.staging-verified`）。已在**不含 libfli 的纯净 `origin/main` worktree**
   上复现完全相同的 JC1/JC5 失败，确认是 main 分支存量问题、与本 PR 无关；且这 4 个文件
   属他人归档目录，本任务不触碰（亦未修改 `ci/` 任何文件）。本 PR 按 CI 实际的
   `checkout-pr` 流程（存在 `pr.diff` 时走 prdiff 模式）执行门禁，JC = pass。

2. **本地执行通道缺 `__fd_chk`**：本机 WSL 用 `/opt/ohos-guest/` 下的**通用 musl** 作
   loader，它没有 OHOS musl 的 fortify 助手 `__fd_chk`，而 `libfli-serial.c` 引用了该符号
   → 本地执行报 `Error relocating ...: __fd_chk: symbol not found`（rc=127）。
   **真实 OHOS sysroot 的 `libc.so` 本身导出 `__fd_chk`**（实测 `nm -D` 见 `T __fd_chk`），
   CI 跑在真 OHOS 环境上不受影响。本地验证按知识库既有条目
   `DRAFT-yosys-0.66-ohos-aarch64-local-run-missing-fd-chk` 的做法，给**本地验证通道**注入
   一个只定义该符号的 aarch64 shim（`QEMU_SET_ENV=LD_PRELOAD=…` 只作用于 guest，
   不污染宿主 x86 进程）。**配方与 test_package 内无任何本地环境假设**（无
   `QEMU_SET_ENV` / `LD_PRELOAD` / 宿主绝对路径）。

### 知识沉淀

- `knowledge/drafts/DRAFT-libfli-findindi-version-regex-quoted-macro` — FindINDI 版本正则与 INDI 2.x 引号格式不匹配；**与平台无关**，故走「回移上游修复」而非平台宏；含与 E092 / E999 的差异化查重
- `knowledge/drafts/DRAFT-conan-extra-cflags-quoted-path-silently-dropped` — `tc.extra_cflags` 里的 `-I"path"` 被 Conan 生成的 CMake quoted string 提前截断，flag 静默失效；并记录「改用 `CMAKE_INCLUDE_PATH` 赋值会覆盖 toolchain 的 PREPEND 列表」这一连锁陷阱
- `manifest.yaml.knowledge_gained` 另记录 2 条包级结论：CMake ≥ 4.0 的 `CMAKE_POLICY_VERSION_MINIMUM` 必须走命令行 `-D`；OHOS 静态库必须显式 `CMAKE_POSITION_INDEPENDENT_CODE=ON`

### 边界合规

- 未触碰框架文件（`SKILL.md` / `references/` / `templates/` / `scripts/` / `ci/` / `index.tsv`）
- 一个 PR 只含一个软件（JC6 合规）
- 未提交任何二进制产物、压缩包、运行时状态文件
- `reports/ci-metadata.json`（CI 侧生成、被 JC1 拦截）已主动剔除，未提交
- 分支名 `feat/libfli-2.0-20221221182632` 精确匹配 `libfli-2.0-20221221182632`（L0n 校验通过）
