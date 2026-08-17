# firmware-resource-package — Broadcom (brcm) 固件资源包验证方法

> 关联知识草稿：`knowledge/drafts/firmware-resource-package-brcm-validation.kv`
> 关联库：linux-firmware-brcm 20260622（PR #3639）
> 状态：draft（draft: true），提交审核后由主编确定最终编号

本文档与同名 `.kv` 配套，详细说明固件资源包（firmware-resource-package）的识别方法、验证流程、
固定来源数据、许可证校验、`package_info()` 约束、依赖边界，以及本 PR 如何使用该方法完成 25 项 smoke 验证。

---

## 1. firmware-resource-package 的识别方法

纯固件资源包具有以下**可机械判定**的特征，命中即按本方法处理：

| 判定维度 | 检查命令 | 通过条件 |
|----------|----------|----------|
| 文件类型 | `file brcm/*.bin brcm/*.fw brcm/*.hcd \| grep -c "data\|MS Windows"` | 全部为二进制 blob/data |
| 无 ELF / 可执行文件 | `find brcm/ -type f -exec file {} \; \| grep -icE "ELF\|executable"` | 结果为 0 |
| 无编译产物 | `find . -name '*.o' -o -name '*.a' -o -name '*.so'` | 无任何 .o/.a/.so |
| 无构建系统 | 检查 `CMakeLists.txt` / `Makefile` / `configure` | 不存在或不产生编译 |
| 无传统测试框架 | 检查 `test/`、`tests/`、`ctest -N` | 无功能测试入口 |

匹配后判定为**纯资源包**：`package_type = "unknown"`、`settings = None`、`options = None`，
`build()` 无编译步骤，仅做补丁应用与文件复制。

---

## 2. 固定 URL、版本、tarball SHA256

**上游项目**：linux-firmware（kernel.org 官方仓库）
`https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git`

**固定版本**：`20260622`

**官方下载源与 SHA256（来自官方 `sha256sums.asc`）**：

| 文件 | URL | SHA256 |
|------|-----|--------|
| `.tar.gz` | `https://cdn.kernel.org/pub/linux/kernel/firmware/linux-firmware-20260622.tar.gz` | `56fadfd4ad1114059c7e8a0171d5e667824807fe1beb621d3cb356c17d20d4ee` |
| `.tar.xz`（conandata.yml 实际使用） | `https://cdn.kernel.org/pub/linux/kernel/firmware/linux-firmware-20260622.tar.xz` | `2b9d8a358e76eb766588609135e53fa548b902c551daae33ee32f26f25e60dbb` |

> `conandata.yml` 的 `sources."20260622"` 使用 `.tar.xz` 及对应 SHA256；
> 两个文件均已在官方 `sha256sums.asc` 中核对，CI 自动为 `cdn.kernel.org` 添加国内镜像 fallback。

---

## 3. Broadcom 许可证校验

| 项 | 值 |
|----|-----|
| 许可证文件 | `LICENCE.broadcom_bcm43xx`（上游 tarball 根目录，属 Broadcom 许可声明） |
| 许可证类型 | Broadcom Proprietary（专有许可） |
| 关键条款 | 允许**再分发**（redistributable），"AS IS" 无担保 |
| 校验方式 | ① 确认 tarball 中存在该文件；② 内容含 Broadcom 专有声明与再分发条款；③ manifest.yaml `license` 字段与之对应 |

固件 blob 属上游官方发布内容，本 PR 仅打包 brcm 子目录并原样再分发，不修改任何固件二进制。

---

## 4. 目录/文件清单、非空、文件类型、无 ELF、逐文件 hash

**brcm 目录统计（20260622 实例）**：

| 指标 | 值 |
|------|-----|
| 文件总数 | 56 |
| 类型分布 | `.bin` 23 个（firmware binary）+ `.fw` 2 个（firmware）+ `.hcd` 1 个（USB descriptor）+ `.txt` 30 个（board config） |
| 总大小 | ~13.5 MB |
| ELF 文件数 | 0 |
| 可编译代码 | 无 |
| 构建系统 | 无 |

**逐文件验证（test_resources.sh，25 项断言）**：

1. 目录存在性/非空（res/brcm/）；
2. 许可证文件存在与内容校验；
3. 关键固件存在性抽样（7 个：`brcmfmac4366c-pcie.bin`、`brcmfmac4350-pcie.bin`、`brcmfmac4330-sdio.bin`、`brcmfmac4334-sdio.bin`、`bcm43xx-0.fw`、`bcm4329-fullmac-4.bin`、`BCM-0bb4-0306.hcd`）；
4. 非空检查（同上 7 个文件，逐字节大小断言）；
5. SHA256 逐文件校验（抽样 4 个：`brcmfmac4330-sdio.bin`、`bcm4329-fullmac-4.bin`、`bcm43xx-0.fw`、`brcmfmac4366c-pcie.bin`，与上游基线 hash 比对）；
6. 无 ELF 检查（`ELF count = 0`）；
7. 文件总数与类型分布（总数 ≥ 50）；
8. 文件名格式（无控制字符异常）。

---

## 5. `res/brcm/` 与目标部署路径

- **Conan 打包路径**：`package()` 中 `copy(self, "*", src=<source>/brcm, dst=<package>/res/brcm)`，
  即包内资源目录为 `res/brcm/`。
- **目标部署路径**：`lib/firmware/brcm/`（Linux 标准固件路径，内核按此路径加载固件）。
- **映射关系**：`res/` → 部署根 → `res/brcm/` 内容部署至 `lib/firmware/brcm/`。
- test_package 通过 `self.dependencies[...].package_folder + "/res/brcm"` 验证该目录在包内存在且非空。

---

## 6. `package_info()` 的 `resdirs` 约束

```python
def package_info(self):
    # 固件资源包：不声明 libs 或 bindirs，仅声明 res 目录
    self.cpp_info.resdirs = ["res"]
```

**约束（kv forbid_2）**：

- ❌ 禁止 `cpp_info.libs = [...]`：固件资源无库文件，声明后下游会错误链接固件数据；
- ❌ 禁止 `cpp_info.bindirs = [...]`：无二进制目录；
- ✅ 仅 `resdirs = ["res"]`，下游以资源方式引用；
- `package_type = "unknown"`，`settings = None`（无平台/编译器/构建配置依赖）。

---

## 7. 无第三方 Conan、内核源码、firmware-tools 和硬件功能验证

| 边界 | 结论 | 说明 |
|------|------|------|
| 第三方 Conan 依赖 | 无 | `requirements()` 为空，`conan_requirements: none` |
| Conan tool_requires | 无 | `conan_tool_requires: none` |
| 内核源码依赖 | 无 | 固件由内核**运行时**加载，打包不依赖内核源码（`instance_kernel_dependency: false`） |
| firmware-tools 依赖 | 禁止 | kv forbid_1：禁止 `requires`/`tool_requires` 引入 `firmware-tools` 等编译工具 |
| 硬件功能验证 | 不做 | 固件烧录/射频功能需真实网卡硬件，CI/打包环境无硬件，`instance_hardware_dependency: false`；以文件完整性 + hash 作为替代验证 |

---

## 8. 可复用到 iwlwifi、ath10k、rtlwifi 等同类资源包

linux-firmware 包含各厂商固件子目录，本方法适用于**所有纯固件资源包子包**：

| 子包 | 许可证 | 部署路径 | 复用方式 |
|------|--------|----------|----------|
| brcm（本 PR） | LICENCE.broadcom_bcm43xx | lib/firmware/brcm/ | 已实施 |
| iwlwifi | LICENCE.iwlwifi_firmware | lib/firmware/ | 替换源子目录 + 许可证文件 + hash 基线 |
| ath10k | LICENCE.QualcommAtheros_ath10k | lib/firmware/ath10k/ | 同上 |
| rtlwifi | LICENCE.rtlwifi_firmware.txt | lib/firmware/rtlwifi/ | 同上 |

复用要点：① 仅提取对应厂商子目录；② 保留对应 `LICENCE.*` 文件；③ 重新计算文件清单与逐文件 hash 基线；
④ 更新 `instance_*` 固定数据；⑤ `package_info()` 保持 `resdirs = ["res"]` 约束不变。

---

## 9. 本 PR 如何使用该知识库完成 25 项 smoke 验证

**流程映射**：

1. **识别**（知识 Layer 1/2）：确认 linux-firmware-brcm 为纯固件资源包 → `package_type="unknown"`、
   无编译、无测试框架，上游测试按 **0/0（N/A）** 记录；
2. **固定来源**（知识固定数据）：采用 `20260622` 版本、官方 CDN URL、SHA256（见第 2 节）；
3. **许可证**（第 3 节）：校验 `LICENCE.broadcom_bcm43xx` 存在与再分发条款；
4. **打包**（第 5/6 节）：`res/brcm/` 目录 + `resdirs` 约束；
5. **smoke 执行**（第 4 节）：test_package 内 `test_resources.sh` 运行 **25 项断言**——
   目录存在/非空（2）+ 许可证（2）+ 关键固件存在（7）+ 非空（7）+ SHA256（4）+ 无 ELF（1）+ 文件总数/类型（1）+ 文件名格式（1）= **25 项，全部通过（25/25，100%）**。

**验证结果（本 PR）**：

| 项 | 结果 |
|----|------|
| conan create（含 test_package） | 通过 |
| conan-verify（G0-G4 + L2/L4/L5） | 通过 |
| smoke 断言 | 25/25（100%） |
| 上游功能测试 | 0/0（N/A，无测试框架） |
| ELF/可执行文件 | 0 |

---

## 关联与元数据

- kv 文件：`knowledge/drafts/firmware-resource-package-brcm-validation.kv`
- 关联库：linux-firmware-brcm 20260622
- 原则引用：R18（预编译优先）、R35（禁止用 conan list 判断 binary）
- similar_to：festvox-kdlpc8k-resource-package
- last_updated：2026-08-11
- contributor_id：probe
