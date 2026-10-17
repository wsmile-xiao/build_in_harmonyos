# 路径 B 知识库扩展申请：依赖在 OH 交叉工具链下不可构建时，用最小符号桩替代整条依赖链

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#6432 chaosread 1.1
- **关联 PR**：`!8846`（`feat/chaosread-1.1`，配方 PR）
- **知识草稿**：`knowledge/drafts/chaosread-1.1-vendored-symbol-stub-for-unbuildable-dep.kv` / `.md`
- **草稿 ID**：`DRAFT-CHAOSREAD-VENDORED-SYMBOL-STUB-FOR-UNBUILDABLE-DEP`
- **提交方式**：草稿与配方归档**同一原子 PR 分支**（`feat/chaosread-1.1`）提交
- **申请日期**：2026-09-10

## 一、为什么这是"可跨仓库复用的知识"

本仓库大量包的适配难点不在上游源码本身，而在**依赖库能否在 OH 交叉工具链下构建**。
本条把"依赖不可构建"的**三条典型死路**（conan-center 预编译 ABI 不匹配 /
autotools 配方与交叉工具链打架 / vendored 整源下载不到）与**一个可复制的出口**
（最小符号桩）一次讲清，并给出**判断该不该用桩的准则**：
「该依赖提供的能力在 CI/目标环境里本就不存在时，为它硬扛跨平台构建链是纯成本」。

## 二、三条死路（chaosread 1.1 实测）

| 路 | 做法 | 原始报错 |
|---|---|---|
| ① 消费 conan-center 预编译 | `libusb/1.0.24`（aarch64 有 prebuilt 的最高版本） | 预编译由 **apple-clang 17 / macOS** 构建，与 `Linux + clang 15` 不匹配 |
| ② 从源码编依赖 | `--build=libusb/1.0.24` | autotools 配方 + OH clang + `--target=aarch64-linux-ohos` 互相打架 → `configure: error: C compiler cannot create executables` |
| ③ 配方内 vendored 整源 | 升到 `libusb-1.0.27` 静态编 | 不在 Debian primary sourcefiles；GitHub 直连被挡 → `HTTPSConnectionPool … Max retries exceeded` |

## 三、判据：依赖能力在验证环境本就不可用

chaosread 的功能是从 **ChaosKey USB 硬件**读真随机熵，而 CI runner 与目标环境
**没有该设备**——即使把真正的 libusb 完整编译进去，CI 上也只会走到
"找不到设备 → 返回错误"这一条路径。

## 四、方案（可复用步骤）

```bash
# 1) 先数符号，不要凭感觉
nm -u build/chaosread.o | grep -o 'libusb_[a-z_]*' | sort -u     # 实测 14 个
```

2. 写桩：`libusb_stub/libusb.h` + `libusb_stub/libusb_stub.c`（合计约 100 行），
   **逐一实现**上述符号并统一返回该库的"不支持"码（`LIBUSB_ERROR_NOT_SUPPORTED`），
   桩内**不得有真实设备 I/O**；
3. 把桩文件写进 `export_sources()`（放在配方自己的目录），使 `conan create`
   **完全自包含** → G2 干净通过；
4. 上游为 autotools 时，若实际只有单一/少量源文件，配方直接驱动 clang
   编译源文件 + 桩文件，绕开 autotools 交叉编译摩擦；
5. 在 `notes.md` 写下三条死路的**原始报错**与最终取舍，供后人审计。

## 五、收益与代价（已在本 PR 中显式声明）

| 项 | 结果 |
|---|---|
| G2（conan create 自包含） | ✅ 干净通过 |
| L2 烟测（`--version` / `--help`） | ✅ 在 OH runner 上可跑 |
| **G3 系统库隔离** | ✅ **`NEEDED` 只剩 `libc.so`** |
| 真实硬件功能 | ⚠️ 桩返回 NOT_SUPPORTED；**CI/目标环境本就无该硬件，等价于"有依赖但无设备"** |

**本申请不回避这一取舍**：PR 与 `notes.md` 均已显式声明"这里换了实现语义"，
以便审计者一眼识别，而非伪装成完整适配。

## 六、验证证据

| 项 | 证据 |
|---|---|
| 依赖三条死路 | 见上表（`configure: error: C compiler cannot create executables` 等原始报错） |
| 桩的符号覆盖 | `nm -u` 列出的 14 个 `libusb_*` 全部在 `libusb_stub.c` 中实现 |
| CI | PR !8846 build **#42993 / #42994 区间 `CI 校验通过`**，L1 测试执行通过 |
| 系统库隔离 | 产物 `NEEDED = libc.so`（无 libusb.so，无其它系统库） |

## 七、查重声明

- **E277**（库自带 vendored 依赖且 registry 无配方时，在 `build()` 内编译子项目到 staging）：
  处理"**子项目能被编出来**"，处置是"编译子项目"；本条处理"**子项目根本编不出来**"，
  处置是"实现符号桩"，判据（`nm -u` 数符号）与产物均不同，**不合并**。
- **E281**（资源型叶子包无编译步骤）：不同场景。
- 正式库以「符号桩 / symbol stub / LIBUSB_ERROR_NOT_SUPPORTED」检索无相关条目。

## 八、请评审确认

1. 是否认可本条目为**路径 B（贡献创新，10 分候选）**评审对象？
2. 「依赖能力在 CI/目标环境本就不可用时，允许以最小符号桩替代」这一准则，
   是否需要写入 `docs/ADAPTATION_GUIDE.md` 并附**强制声明要求**（notes.md 必须写明
   语义取舍，防止被当作完整适配）？
3. 桩方案带来的 G3 系统库隔离收益，是否建议作为正面指标计入评审？
