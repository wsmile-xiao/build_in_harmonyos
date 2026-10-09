- **三方库名称**：libubi
- **上游版本**：2.3.1（上游源码 mtd-utils 2.3.1；Debian/Ubuntu 源包 `mtd-utils 2.3.1-3` 编出 `libubi-dev`）
- **上游仓库地址**：https://git.infradead.org/mtd-utils.git （发布源 tarball：https://infraroot.at/pub/mtd/mtd-utils-2.3.1.tar.bz2 ，sha256 `03d9dc58ad10ea3549d9528f6b17a44d8944e18e96c0f31474f9f977078b83dc`）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（依据 libogg/1.3.5.1 的 direct-cc 先例完成适配）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | mtd-utils 上游测试套件由 `./configure --with-tests` 开启，本次适配显式 `--without-tests --disable-unit-tests` 关闭（设备相关，无法在 headless 构建机执行） |
| 集成测试 | 0 | 同上，未纳入本次构建 |
| 其他测试 | 0 | — |
| **合计** | **0** | 上游测试套件在 OHOS 适配场景下被刻意关闭，非遗漏 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游单元套件已关闭 |
| 集成测试 | 1 | +1 | 安装后消费者端到端流程（test_package.c） |
| 鸿蒙特有测试 | 0 | 新增 | — |
| **合计** | **1** | **+1** | 1 个端到端消费者流程，含 **4 个 CHECK 断言**，全部通过 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例（上游测试套件整体未纳入构建）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游无可在 headless 构建机执行的 UBI 消费者测试，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为核心 UBI 开发库补全 1 个安装后消费者端到端测试，覆盖真实公共 API 工作流
> - **补全原因**：UBI 设备（`/dev/ubi_ctrl`、`/dev/ubiN`）仅存在于带内核 UBI 子系统的目标机，headless 构建机无设备；上游自带测试套件设备相关、无法运行，故以消费者视角验证库可用性
> - **新增测试文件清单**：
>   1. `archives/l/libubi/2.3.1-3/test_package/test_package.c` — 链接打包后的 `libubi.a` 并运行，断言：①`libubi_open()` 在无设备主机返回 NULL（符合文档行为）；②`struct ubi_mkvol_request` 公共请求结构可正常使用；③公开 UBI 常量（`UBI_VOL_NUM_AUTO`/`UBI_MAX_VOLUME_NAME`）可达；④端到端完成标记。4 个断言全部通过。

## 验证结果

- 编译状态：通过（direct-cc 路线：`./configure` 仅生成 `include/config.h`，再用校验过的 OHOS clang 直接编译，llvm-ar 将 6 个静态归档合并为单一自包含 `libubi.a`）
- 上游测试用例通过率：N/A（上游测试套件已按设计关闭）
- 新增测试用例通过率：4/4（100%，1 个端到端消费者流程、4 个 CHECK 断言全过）

## 补充说明

- **静态库优先**：libubi 及 mtd-utils 其余开发库在上游被声明为 `noinst_LIBRARIES`，`make install` 不安装它们；本配方手动 `make <lib>.a` 后合并安装，符合上游行为，亦满足 R4/R26 静态优先约定。**仅产出静态库 `libubi.a`，不产出 `.so`**，`validate()` 显式拒绝 `shared=True`。
- **零外部依赖**：关闭 zlib/lzo/zstd/selinux/crypto/ubifs/jffs/lsmtd/ubihealthd 后，`libubi.a` 自包含（仅依赖 libc），`llvm-nm` 确认无外部未定义符号。
- **OHOS 运行签名**：test_package 消费者二进制经 `binary-sign-tool sign` 自签，并断言 `.codesign` 段恰为 1 个后运行（鸿蒙 PC 要求 ELF 带签名段方可执行）。
- **conan-verify 八道门禁全部通过**：G0/G1/G2/G3/G4 + L2/L4/L5（`conan create` 干净构建 + 安装后消费者端到端测试）。
- **PF9 说明**：本 PR 仅变更 `archives/l/libubi/2.3.1-3/` 单包目录内文件，未新增软件级 `archives/l/libubi/README.md` 或 `commands.json`，不涉及 PF9 命中路径；PF1–PF8 已由 conan-verify 的 G0–G4 + L2/L4/L5 实测覆盖通过。
- 已知限制：UBI 运行时行为需在真实 UBI 设备上验证；本适配保证库可正确编译、链接并以消费者身份完成公开 API 工作流。
