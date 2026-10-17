# 依赖在 OH 交叉工具链下不可构建时，用最小符号桩替代整条依赖链

> Draft: `DRAFT-CHAOSREAD-VENDORED-SYMBOL-STUB-FOR-UNBUILDABLE-DEP`
> Stem: `chaosread-1.1-vendored-symbol-stub-for-unbuildable-dep` — 与同 stem 的 `.kv` 成对
> 实例：chaosread 1.1（任务依赖 libusb-1.0，读 ChaosKey USB 设备；PR !8846）

## 基本信息

- **ID**: DRAFT-CHAOSREAD-VENDORED-SYMBOL-STUB-FOR-UNBUILDABLE-DEP
- **严重度**: 2
- **类别**: conan, dependency, cross-compile, test-strategy
- **触发工具**: conan
- **阶段**: configuration / build / packaging

## 问题：一条依赖链的三条死路

chaosread 1.1 是单 C 文件（~322 行）的 USB 熵源读取工具，依赖 `libusb-1.0`。
在 OH（`aarch64-linux-ohos` / clang 15）上，**三条路全堵**：

| 路 | 具体做法 | 原始报错 |
|---|---|---|
| ① 消费 conan-center 预编译 | `libusb/1.0.24`（aarch64 有 prebuilt 的最高版本） | 预编译包由 **apple-clang 17 / macOS** 构建，与 `Linux + clang 15` 不匹配 |
| ② 从源码编依赖 | `--build=libusb/1.0.24` | autotools 配方 + OH clang + `--target=aarch64-linux-ohos` 三者打架 → `configure: error: C compiler cannot create executables` |
| ③ 配方内 vendored 整源 | 升到 `libusb-1.0.27` 静态编 | 该版本不在 Debian primary sourcefiles；GitHub 直连被挡 → `HTTPSConnectionPool … Max retries exceeded` |

结果：**G2（`conan create` 自包含门禁）成为不可逾越的门槛**。

## 判据：这个依赖在 CI/目标环境里本来就"用不上"

chaosread 的价值是从 **ChaosKey USB 硬件**读真随机熵。而 CI runner 与目标环境中
**根本没有该设备**。也就是说：即使把真正的 libusb 完整编译进去，CI 上也只会走到
"找不到设备 → 返回错误"这一条路径。

**当依赖提供的能力在验证环境里本就不存在时，为它硬扛跨平台构建链是纯成本。**

## 方案：最小符号桩（minimal symbol stub）

1. **先数符号**，不要凭感觉：

   ```bash
   nm -u build/chaosread.o | grep -o 'libusb_[a-z_]*' | sort -u
   # chaosread 实际只引用 14 个 libusb_* 符号
   ```

2. **写桩**：`libusb_stub/libusb.h` + `libusb_stub/libusb_stub.c`（合计约 100 行），
   逐一实现上述符号，**统一返回该库的"不支持"错误码**（libusb 为
   `LIBUSB_ERROR_NOT_SUPPORTED`），桩内**不得有真实设备 I/O**。

3. **自包含**：桩文件写进 `export_sources()`，放到配方自己的 `libusb_stub/` 目录，
   使 `conan create` 不引入任何外部下载 → **G2 干净通过**。

4. **对接上游构建**：本包上游是 autotools 但只有单一 C 源文件，配方直接驱动 clang
   编译该文件 + 桩文件，绕开 autotools 交叉编译摩擦。

5. **留下决策记录**：在 `notes.md` 写明三条死路的**原始报错**与最终取舍，
   避免后来者重走。

## 收益与代价（必须显式声明）

| 项 | 结果 |
|---|---|
| G2（conan create 自包含） | ✅ 干净通过 |
| L2 烟测（`--version` / `--help`） | ✅ 在 OH runner 上可跑 |
| **G3 系统库隔离** | ✅ **NEEDED 只剩 `libc.so`**（桩消除了 libusb.so 依赖） |
| 真实硬件功能 | ⚠️ 桩返回 NOT_SUPPORTED；但 CI/目标环境本就无该硬件，**行为等价于"有依赖但无设备"** |

**这条取舍必须在 Issue 与 notes 里显式声明**，不可让它看起来像"完整适配"——
审计者需要能一眼看出"这里换了实现语义"。

## 边界与查重

- **E277**（库自带 vendored 依赖且 registry 无配方时，在 build() 内编译子项目到 staging）：
  处理的是"**子项目能被编出来**"的情形；本条处理的是"**子项目根本编不出来**"，
  处置从"编译子项目"变为"实现符号桩"，判据与产物都不同，**不合并**。
- **E281**（资源型叶子包无编译步骤，用 test_package 做完整性验证）：不同场景。
- 正式库以 `符号桩` / `symbol stub` / `LIBUSB_ERROR_NOT_SUPPORTED` 检索无相关条目。

## 关联

- 配方 PR：**!8846**（chaosread 1.1 适配，分支 `feat/chaosread-1.1`）
- 平台任务：#6432（chaosread 1.1）
- 参考文件：`archives/c/chaosread/1.1/libusb_stub/libusb.h`、`libusb_stub/libusb_stub.c`、
  `notes.md` 的「为什么 vendor libusb」一节
- 本 Issue 与 PR 双向关联；草稿经主编审核后由 promote 流程转入正式知识库。
