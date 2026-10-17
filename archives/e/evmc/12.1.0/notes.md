# evmc 12.1.0 — HarmonyOS PC (aarch64) 适配说明

## 一、库简介

EVMC（Ethereum Client-VM Connector API）是 Ethereum 客户端与虚拟机实现之间的
**连接器 ABI**。它本身几乎不含"执行引擎"，而是一套稳定的 C ABI 头文件加若干可选
的辅助静态库，让 geth / evmone / besu 这类客户端与 VM 实现可以解耦演进。

上游 12.1.0 的产物分为两部分：

| 产物 | 类型 | 说明 |
|---|---|---|
| `evmc/evmc.h`, `evmc/evmc.hpp` | 头文件 | 核心 C ABI 与 C++ 包装（`evmc::VM` / `evmc::Result` / `evmc::Host`） |
| `libevmc-loader.a` | 静态库 | 运行期 `dlopen()` 加载 VM 共享库（`evmc_load_and_configure`） |
| `libevmc-instructions.a` | 静态库 | 指令名 / gas 成本表 |
| `libtooling.a` | 静态库 | VM 自测工具链 |
| `evmc` / `evmc-vmtester` | 可执行文件 | CLI 工具（本配方只用于跑上游测试，不打包） |

## 二、适配路径

**路径 A（依赖库适配）**。上游是普通 CMake 工程，无汇编、无私有接口、无闭源依赖，
适配工作集中在两处：**去掉 Hunter 包管理器的联网引导**，以及**让运行期测试真正执行**。

## 三、上游依赖 Hunter 的处理（patch 0001）

上游用 [Hunter](https://github.com/cpp-pm/hunter) 获取 GTest / CLI11。Hunter 是一个
**联网 bootstrap 的包管理器**：它通过 `HunterGate()` 在 configure 阶段下载
`hunter.cmake` 并自举，在离线 / 交叉编译环境下无法工作。

patch 0001 做两件事：

1. **保留 `HunterGate()` 调用但令其进入 disabled 模式**（`HUNTER_ENABLED=OFF`），
   于是 `hunter_add_package()` 退化为 no-op，GTest / CLI11 改由 `find_package()`
   从 Conan 的 CMakeDeps 包解析；
2. **把 `EVMC_TOOLS` / `EVMC_EXAMPLES` 从 `cmake_dependent_option` 改成普通 `option`**。
   上游写法是 `cmake_dependent_option(EVMC_TOOLS ... EVMC_TESTING OFF)`，当
   `EVMC_TESTING=ON` 时它反而把两个开关强制成 `ON`，而 `test/vmtester/CMakeLists.txt`
   会调用 `evmc_add_vm_test()`，该函数在 `evmc::evmc-vmtester` 目标不存在时
   `FATAL_ERROR` —— 于是测试目录根本无法 configure。

> **注意**：这两个开关必须是 **CMake cache 变量**。上游用 `option()` 声明，
> 而 `option()` 只在已存在**同类型 cache 条目**时才尊重外部值；Conan 的
> `tc.variables` 生成的是普通 `set()`，会被 `option()` 直接丢弃并回落到默认值，
> 静默把测试套件关掉。配方里因此使用 `tc.cache_variables`。

## 四、musl 运行期差异（patch 0002）

`test/vmtester/` 中 `nonexistingvm` 用例断言 `dlerror()` 的文本。glibc 返回
`No such file or directory`，musl（OpenHarmony 使用的 C 库）返回 `No such file`。
patch 0002 放宽该正则同时接受两种措辞，**不改变功能行为与退出码**。

## 五、测试结果

测试在 `ohos-aarch64-run` profile 下执行：aarch64 交叉编译，经
`CMAKE_CROSSCOMPILING_EMULATOR` 用 qemu + OHOS musl 运行根真实执行。

### 5.1 上游 CTest 套件

上游注册 **146** 个用例，**实测执行 146 个，通过 146 个（100%），失败 0**。

| 套件 | 执行数 | 通过 |
|---|---|---|
| `evmc/unittests/` | 115 | 115 |
| `evmc/evmc-tool/` | 14 | 14 |
| `evmc/vmtester/` | 9 | 9 |
| `evmc/cmake_packge/` | 6 | 6 |
| `evmc/examples/` | 2 | 2 |
| **合计** | **146** | **146** |

```
100% tests passed, 0 tests failed out of 146
Total Test time (real) =  38.84 sec
```

> 上游用例数（146）与实测执行数（146）一致，**没有跳过任何用例**。
> 这一套不是"编译通过就算过"——`evmc/vmtester/` 与 `evmc/examples/` 会在运行期
> `dlopen()` 一个 VM 共享库并真实执行 EVM 字节码，必须能跑才能通过。

### 5.2 鸿蒙特有消费者端到端用例（rule 12）

`test_package/` 构建一个**真实的 EVMC host**，走完整消费链路：

1. 用打包的 `evmc::MockedHost` 建立 host 并注入账户状态；
2. 用打包的 `libevmc-loader.a`（`evmc_load_and_configure`）从磁盘 **`dlopen()`**
   真实的 `libexample-vm.so`，再交给 `evmc::VM` RAII 托管；
3. 通过 `evmc::VM::execute()` 执行真实 EVM 字节码
   （`PUSH1 0x2a PUSH1 0x00 MSTORE PUSH1 0x20 PUSH1 0x00 RETURN`）；
4. 校验返回状态、gas 消耗、32 字节输出内容，以及 `libevmc-instructions.a`
   的指令名 / gas 表；
5. 对同一个 VM 实例再跑一次 `SSTORE(0,1)`，验证实例可复用且回调真的写进 host 存储。

16 项检查全部通过：

```
CONSUMER_RESULT checks=16 passed=16 failed=0
CONSUMER_VERDICT PASS
```

**为什么 `libexample-vm.so` 由 test_package 自己构建**：上游把
`evmc::example-vm` 编成共享库，但 `install()` 规则只覆盖 `include/evmc` 与
`lib/` 下的静态库，**并不安装它**。消费者无法从 evmc 包拿到这个 VM，
所以 test_package 从**同一版本的上游源码**（sha256 校验一致）自行构建它，
以保证 `dlopen()` 这一环是真实的，而不是用桩函数糊弄过去。

## 六、打包与 CMakeDeps 要点

- **组件拆分**：`package_info()` 把库拆成 `headers` / `cpp` / `loader` /
  `instructions` / `tooling` / `mocked_host` 六个组件，消费者可只依赖所需部分。
- **`tooling` 归档名**：上游 `lib/tooling/CMakeLists.txt` 是四个 `add_library()`
  中**唯一没有设置 `OUTPUT_NAME`** 的，因此装出来是 `libtooling.a` 而非
  `libevmc-tooling.a`。配方据此声明 `libs = ["tooling"]`；若照名字直觉写
  `evmc-tooling`，CMakeDeps 会在消费者 configure 阶段直接报
  `Library 'evmc-tooling' not found in package`。
- **`lib/cmake/evmc/` 被移除**：上游自带的 config 包与 Conan CMakeDeps 生成的
  config 包会同时出现在 `CMAKE_PREFIX_PATH` 上，产生二义性，故打包时删除前者。

## 七、证据文件

| 文件 | 内容 |
|---|---|
| `evidence/conan-create-ohos-aarch64-run.log` | 完整 `conan create` 日志 |
| `evidence/ctest-summary.txt` | CTest 汇总行 |
| `evidence/consumer-e2e-output.txt` | 消费者端到端用例完整输出 |

## 八、复现命令

```bash
conan create . -pr:h=ohos-aarch64-run -pr:b=default -c tools.build:jobs=4
```
