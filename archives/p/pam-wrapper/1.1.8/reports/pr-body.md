- **三方库名称**：pam-wrapper
- **上游版本**：1.1.8
- **上游仓库地址**：https://gitlab.com/cwrap/pam_wrapper
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C（高难度挑战）
- **使用知识库**：E077、E200、E223 draft；新增两个 pam-wrapper 知识草稿

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 23 | 来源：`tests/test_pam_wrapper.c`，由 CTest/CMocka 驱动 |
| 集成测试 | 0 | 上游未单列其他自动测试入口 |
| 其他测试 | 0 | Python 测试因本配置未启用 binding，不计入统计 |
| **合计** | **23** | 1 个 CTest target 内含 23 个独立 CMocka case |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 23 | 不变 | HarmonyOS 目标端 23/23 PASS，未修改 case 和期望值 |
| 集成测试 | 1 | +1 | 安装包 consumer 完成 `dlopen`、`libpamtest` 和 `pam_matrix` 认证 |
| 鸿蒙特有测试 | 0 | 不变 | ELF 签名与启动环境是测试执行前置，不拆分计数 |
| **合计** | **24** | **+1** | 不按内部断言、重复运行或构建模式扩充计数 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

四份 patch 只调整 CMake 的 PAM include/library 路径，使 configure、库、MODULE
和上游测试目标绑定同一个 Conan `linux-pam/1.7.2` 包。配方默认开启
`UNIT_TESTING`，使用 `cmocka/2.0.2` 作为 `test_requires`，并在 CTest 前处理
实际参与运行的 build-tree ELF；未修改 `tests/test_pam_wrapper.c` 的 case、输入或
预期结果，也未跳过失败 case。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

上游已有 23 个 CMocka 用例。本适配额外增加 1 个安装包 consumer 集成流程，用于
验证安装后的 `libpam_wrapper.so`、`libpamtest.so`、`pam_matrix.so`、PAM service
和 passdb 能够完整联动；该流程不属于“上游无测试用例后补全”的情形。

新增测试文件：`archives/p/pam-wrapper/1.1.8/test_package/test_pam_wrapper.c`。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：23/23（100%）
- 新增测试用例通过率：1/1（100%）

## 补充说明

### 高难度挑战库申请

申请按高难度挑战库候选评审，最终等级和分值以评审结论为准。详细依据、计数规则
和不申报边界见：

`archives/p/pam-wrapper/1.1.8/reports/high-difficulty-evidence.md`

本 PR 的难点是让多动态目标 PAM 加载图、Conan 精确依赖、`LD_PRELOAD` 的
pre-main 生命周期、HarmonyOS 目标端 ELF 签名和完整上游 CMocka 套件在同一真机
流程中闭环，而不是以 patch 行数或内部断言数量扩大计分。

### 知识库补充

- 复用 E077：ELF 修改后移除旧 `.codesign` 并重新签名。
- 复用 E200：在 HarmonyOS/musl 上以真实 consumer 验证 `LD_PRELOAD`。
- 复用 E223 draft：将 Conan 精确依赖路径桥接给上游 CMake legacy 查找。
- 新增 `knowledge/drafts/DRAFT-pam-wrapper-ctest-elf-runtime-closure.{kv,md}`。
- 新增 `knowledge/drafts/DRAFT-pam-wrapper-preload-startup-context.{kv,md}`。

两个新增草稿分别记录 CTest 前构建树完整 ELF 加载闭包的签名边界，以及 preload
库在 `main()` 前捕获配置时必须由 launcher 预创建夹具、在 `exec` 环境一次性
注入变量的生命周期要求。草稿不修改正式 `knowledge/graph/index.tsv`。

### 依赖与验证环境

- 关联 Issue：#1763
- 官方源码：https://ftp.samba.org/pub/cwrap/pam_wrapper-1.1.8.tar.gz
- 源码 SHA-256：`6549c0b3e41d1ebe0c94a1be63c25eec918191462b602ab6f47d4a5fa709c3e4`
- 目标环境：HarmonyOS 6.0 / aarch64
- 运行依赖：`linux-pam/1.7.2`
- 测试依赖：`cmocka/2.0.2`，仅作为 Conan `test_requires`
- 仓库 CI：L0/L1/L4/L5 PASS；库包无 `bin/`，L2 正常跳过

### 证据

- CTest 日志 SHA-256：`9660199e69663db0bcced0d4bf802d3d6e318219030ecad4e731bd7806c9ed87`
- 仓库 CI 日志 SHA-256：`a181e7753188788ad47bd24a4196d2d68e47208a377d4949a9ba3370283d59c7`
- Conan verify 报告 SHA-256：`8c5d26bc22cc70ec7371e01ebd55639cb59a7ebc879a87aaf1731294e4b7a50e`

### 申报边界

- 不把前置依赖 `linux-pam/1.7.2` 的独立适配工作量重复计算。
- 不声明 Python binding 或 static 模式已验证。
- 不把 consumer 内部断言拆分成多个新增测试流程。
- 不申报独立服务搭建；PAM service 文件只是测试夹具。

### 验证命令

```sh
conan create archives/p/pam-wrapper/1.1.8
CI_PACKAGES="archives/p/pam-wrapper/1.1.8" zsh ci/conan/build_and_test.sh
```
