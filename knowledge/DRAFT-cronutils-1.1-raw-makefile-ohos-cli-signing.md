# cronutils 1.1：raw Makefile CLI 在 HarmonyOS 上的构建、签名与 Conan 消费验证

- **草稿 ID**: `DRAFT-cronutils-1.1-raw-makefile-ohos-cli-signing`
- **来源**: `cronutils/1.1` HarmonyOS PC 适配实战
- **分类**: `raw-makefile / conan / cli-tool / elf-signing / consumer-test`
- **状态**: `VERIFIED DRAFT`，路径 B 难度候选，待知识库审核
- **Issue/PR**: 本轮按任务要求不记录

## 适用场景

cronutils 1.1 是一个没有 configure、CMake 或上游自动化测试的老旧 C
命令行工具集。源码通过 raw Makefile 生成 `runalarm`、`runlock` 和
`runstat` 三个 ELF 工具，在 HarmonyOS PC（AArch64、musl、HMDFS）上适配
时，构建成功并不等于 Conan 包可以被消费者执行。

本案例适合以下组合场景：

- 上游只有 raw Makefile，构建规则短小但隐含了 source/build 目录和工具链假设；
- 目标是 HarmonyOS/OHOS，而不是普通 Linux；
- Conan 包交付的是 `bin/` 下的命令行 ELF，而不只是 `.a` 或 `.so`；
- 需要由 `conan create` 自动执行 test_package，并在真机上形成可追溯证据。

## 问题与错误签名

### 1. 老旧 POSIX 头文件差异

`runstat.c` 直接使用 `HOST_NAME_MAX`。在目标头文件集合中该宏不一定已经
定义，构建阶段会出现未声明或相关预处理错误。旧源码还依赖
`clock_gettime()`、`dprintf()` 等 POSIX/GNU 接口，不能只凭“目标是 Linux”
的经验判断头文件可见性。

### 2. OHOS 链接参数不能照搬 Linux

上游 Makefile 为 Linux 使用 `-lrt`。本次目标的 HarmonyOS libc 已提供
`clock_gettime()`，继续强制链接 standalone `-lrt` 会把不存在或不应进入
依赖图的库带入构建。另一方面，CI worker 需要使用 HNP 工具链的 linker，
本地 DevEco 交叉构建又需要一个可配置的 SDK linker 路径。

### 3. 构建和打包成功，但真机执行报权限错误

首轮 shadow CI 的关键错误为：

```text
PermissionError: [Errno 13] Permission denied:
.../conan-home/p/b/.../p/bin/runalarm
```

这不是普通 Unix 执行位问题。首轮包内文件虽然已经是 `0750`，但没有有效
HarmonyOS `.codesign` 数据，内核拒绝从 Conan package cache 加载它们。
因此只在 `package()` 中 `chmod 755` 不能解决问题。

### 4. CLI 包在 L0k 需要软件级命令元数据

`package_type = "application"`、`cpp_info.bindirs = ["bin"]` 和实际 CLI
产物会触发 R38/L0k 检查。若缺少软件级
`archives/c/cronutils/commands.json`，配方即使能编译也会在质量门禁阶段失败。

## 根因拆解

1. **构建系统边界**：Conan 的 build folder 与源代码目录不是同一目录；
   对 raw Makefile 项目直接调用默认构建命令会遇到 Makefile 不在当前工作目录、
   或宿主 `make`/`CC` 选择覆盖目标工具链的问题。cronutils 的三个目标足够简单，
   直接复现上游 target/source 映射比引入一层 host make 更可控。
2. **API 可见性边界**：老代码没有为现代 POSIX 头文件环境提供完整的特性宏和
   `HOST_NAME_MAX` fallback。以 `_XOPEN_SOURCE=700` 统一打开 POSIX 声明，并对
   可选宏增加受保护 fallback，属于最小兼容改动。
3. **平台链接边界**：Linux 的 `-lrt` 不是 OHOS 的必需依赖。配方应按目标 OS
   选择库参数，而不是把 Makefile 的 Linux 链接行原样复制到所有平台。
4. **可执行交付边界**：HarmonyOS 的 ELF 签名是可执行包的交付条件。构建树中
   看到 ELF 或普通 Unix mode 不能证明真机可执行；签名必须作用于最终 package
   目录中的文件，且发生在 test_package 消费之前。
5. **质量门禁边界**：CLI 工具需要同时满足 R38 元数据、Conan package 内容、
   真机执行和命令行为测试。仅验证 `conan create` 不足以替代消费者验证。

## 推荐实现

### 1. 固定源码身份

使用 Debian Snapshot 中可重现的 upstream archive，不依赖易变的发行版镜像：

```text
URL:
https://snapshot.debian.org/archive/debian/20110723T212944Z/pool/main/c/cronutils/cronutils_1.1.orig.tar.gz
SHA256:
28a5bbba67a1977be553aacc0b4087b61fef83857f8d7703b9bb823c07454035
```

配方在 `get()` 中显式传递 URL、SHA256 和 `strip_root=True`，避免把源码根目录
名称和下载器推断出的文件名当作隐含输入。

### 2. 直接复现三个上游目标

保持上游的 target/source 关系：

| 目标 | 源文件 |
|------|--------|
| `runalarm` | `runalarm.c` + `subprocess.c` |
| `runlock` | `runlock.c` + `subprocess.c` + `tempdir.c` |
| `runstat` | `runstat.c` + `subprocess.c` + `tempdir.c` |

配方从 `tools.build:compiler_executables` 读取字典并取 `c` 键：

```python
compilers = self.conf.get(
    "tools.build:compiler_executables",
    default={},
    check_type=dict,
) or {}
cc = compilers.get("c", "clang")
```

OHOS 使用 `_XOPEN_SOURCE=700`；`runstat.c` 保留自身需要的 `_GNU_SOURCE`
定义。`runlock` 的状态变量初始化为 `EX_OSERR`，消除 clang 对未初始化返回
值的警告，同时给异常路径确定的退出语义。

### 3. 按目标 OS 选择 linker 和库

- OHOS：默认使用 `/data/service/hnp/bin/ld`，允许通过
  `user.ohos:ld_path` 或 `OHOS_LD` 覆盖本地 SDK linker；不追加 `-lrt`。
- Linux：保留 `-lrt`，兼容旧 Linux libc 环境。
- 不把绝对设备路径写入知识草稿以外的交付命令，不把设备 IP、私钥或 token
  写入配方、manifest、notes 或 PR。

### 4. 在 package() 对最终 OHOS ELF 进行自签

最终 package 文件必须按以下顺序处理：

```sh
llvm-objcopy --remove-section .codesign "$binary" 2>/dev/null || true
binary-sign-tool sign \
  -inFile "$binary" \
  -outFile "$binary.signed" \
  -selfSign 1
mv "$binary.signed" "$binary"
chmod 755 "$binary"
```

配方实现中的关键点：

- 只对 `settings.os == "OHOS"` 的最终命令行 ELF 执行签名；
- 优先读取 `user.ohos:sign_tool`、`OHOS_SIGN_TOOL` 或 PATH，再回退到 worker
  约定路径；
- 签名输出写入临时文件，确认文件存在后再 `os.replace()`，避免签名失败时
  覆盖原始可执行文件；
- `binary-sign-tool` 成功后重新设置执行位，因为签名工具可能改变文件 mode；
- 本机没有签名工具时只能记录 warning 并完成静态交叉构建，不能把结果宣称为
  真机交付通过；真正的 OHOS runner 必须提供签名工具并执行消费者测试。

### 5. test_package 进行行为而非文件存在性验证

本案例的 test_package 使用绝对路径定位被测包 `bin/`，避免依赖开发机 PATH，
并执行 18 个断言：

- 三个命令存在；
- 三个命令的 `-h` 返回 0 且输出 Usage；
- `runalarm` 转发子进程退出码；
- `runalarm -t 1` 对睡眠子进程返回超时状态；
- `runlock` 验证持锁进程与阻塞进程的互斥结果；
- `runstat -f` 返回子进程状态，并产生 `exit_status`、`elapsed_time` 记录。

锁文件和统计文件使用显式可写路径，避免上游默认的 `/tmp/cronutils-<user>`
路径在 HMDFS/只读临时目录环境中造成无关失败。

## 验证证据

| 阶段 | 结果 | 证据 |
|------|------|------|
| W0 依赖检查 | 通过 | 无外部 Conan 依赖 |
| W1 源码审计 | 通过 | 固定 tarball、raw Makefile、三个 target 映射 |
| W2 Conan 配方 | 通过 | `conanfile.py`、`conandata.yml`、OHOS profile |
| W3 test_package | 通过 | 18 个真实行为断言 |
| 本机交叉构建 | 通过 | DevEco BiSheng clang 生成 AArch64 OHOS ELF |
| 首次真机尝试 | 失败且已定位 | 未签名 package ELF，`PermissionError: [Errno 13]` |
| 修复后真机 shadow CI | 通过 | Conan create/package、签名、消费者执行全部成功 |
| L0/L1/L2/L4/L5 | 全部通过 | `commands.json`、test_package、三个 `--help`、包内容检查 |

修复后设备证据：

```text
PASS: cronutils packaged consumer test (18/18 assertions)
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: runalarm --help OK, runlock --help OK, runstat --help OK
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content
Build Summary: Success: 1, Failed: 0
```

三个最终包内 ELF 均通过 `llvm-readelf -S` 检查存在一个 `.codesign` 段，
并在 AArch64 HarmonyOS 设备上实际启动。这个顺序证实了“签名后再消费”是
必要的，而不是只满足静态文件检查。

## 为什么是 B 类候选

本草稿不是把普通的“写一个 Conan 配方”包装成难题，而是记录了一个可复现的
跨层闭环：

1. 固定历史源码并审计 raw Makefile；
2. 处理 OHOS 头文件、特性宏和 libc 链接差异；
3. 处理 Conan host/build profile 和 source/build 目录边界；
4. 补足 CLI 包的 R38 软件级元数据；
5. 从真机首轮 `PermissionError` 反推 HMDFS/ELF 签名根因；
6. 将最小签名修复放到 package()，再用 18 个消费者断言和 L0-L5 证据闭环。

它的困难点来自构建系统、平台 ABI、文件系统执行策略、包元数据和真机验证
之间的联动，而不是单一编译错误。最终状态有首轮失败记录、修复前后对照和
真机成功证据，适合作为路径 B 难度候选提交；是否正式认定仍由知识库维护者
审核。

## 非适用边界

- 只交付静态库或共享库、没有 `bin/` ELF 的 Conan 包不需要本条 CLI 签名流程；
- 链接器已经生成并且验证为有效系统签名的产物，不应无条件二次签名；
- 需要在构建过程中立即执行新生成宿主 ELF 的 bootstrap 项目，应采用构建期
  wrapper 签名方案，不能等到 package()；
- 没有真实设备或等价 OHOS 执行环境时，只能报告交叉构建/静态检查，不能报告
  真机消费者通过。

## 禁止模式

- 不要把 `chmod 755` 当成 HarmonyOS ELF 可执行性的充分条件；
- 不要只在构建树里签名，随后把未签名副本重新 copy 到 Conan package 目录；
- 不要让 `binary-sign-tool` 直接覆盖已有 `.codesign`，应先移除旧段并输出到
  临时文件；
- 不要因为上游没有 `make check` 就把“无上游测试”写成“测试通过”，必须用
  test_package 的真实消费者行为测试补位；
- 不要直接用 `runalarm` 等命令名假设 PATH 一定包含被测包 `bin/`，测试应使用
  包元数据拼接绝对路径或显式注入运行环境；
- 不要把设备 IP、SSH 私钥路径、认证 token 写入知识草稿、manifest、notes 或
  PR。

## 关联知识与交付

- 与 E392 的 raw Makefile Conan 三陷阱相关，但本案例增加了旧 POSIX CLI 的
  特性宏、OHOS `-lrt` 边界、真机首轮失败到签名修复的完整证据。
- 与 E077 的 ELF 签名规则相关，但本案例给出 Conan `package()` 对最终 CLI
  产物签名，以及签名后 18/18 消费者验证的库级落地。
- 与 E424 的 `commands.json`/R38 相关，本案例将其作为 CLI 三方库交付的前置
  质量门禁一起验证。
- 交付文件：`archives/c/cronutils/1.1/**` 与软件级
  `archives/c/cronutils/commands.json`；本草稿仅保留在 `knowledge/` 根目录，
 不修改正式知识图谱、正式文档和索引。
