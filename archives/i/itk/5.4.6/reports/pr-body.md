## PR 信息

- **三方库名称**：itk
- **上游版本**：5.4.6
- **上游仓库地址**：https://github.com/InsightSoftwareConsortium/ITK
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）+ 路径 C（高难度挑战）
- **使用知识库**：E265、E266、E267、E268、E269、E270、E271、E272、E273（本 PR 的知识图谱草稿）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 532 | ITKCommon、VNL、MetaIO 及支持库的编译型行为测试 |
| 集成测试 | 1 | `itkCMakeConfigurationTest` 验证生成的 CMake 配置 |
| 其他测试 | 85 | 43 个 KWStyle 检查和 42 个 Doxygen group 检查 |
| **合计** | **618** | `BUILD_TESTING=ON` 的 CTest JSON 清单，disabled=0 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 未新增或修改上游单元测试 |
| 集成测试 | 0 | 不变 | 未新增或修改上游集成测试 |
| 鸿蒙特有测试 | 1 | +1 | Conan `test_package` 在认证真机完成构建、链接并运行 `test_itk_consumer` |
| **合计** | **1** | **+1** | 新增测试独立统计，不替代上游 618 个 CTest 入口 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游测试源码和 618 项清单均保持不变；补丁只处理构建平台选择、离线输入和目标能力绑定。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增 Conan 消费者测试用于验证 HarmonyOS PC 安装包的 `find_package`、静态链接和运行，不作为上游测试缺失的替代品。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：618/618（100%）
- 新增测试用例通过率：1/1（100%）

- 上游构建完成 2209/2209 个 Ninja edge；CTest failed/skipped/disabled 均为 0。
- 上游清单 SHA256：`b269a30b908fa17cbbb0e63b60115c3016561a1abe3ca7c9526d6bfbde69eff6`。
- 上游 CTest 原始日志 SHA256：`7258864c1164f98509b51c6e0aa5fad962f83ff6f34aceb2975a4d990180f438`。
- GitCode checkout 只消费文本 PR patch；14 个 CID 对象现以 canonical Base64 文本运输，并只在 `export_sources()` 隔离目录恢复原字节。运输正负例 6/6、导出运行时 8/8；fresh Conan export 含 manifest 与 14/14 个原始 CID 对象（992270 bytes）、零 encoded 文件，逐文件 SHA256 一致；recipe revision：`272725e9dca1c58a5f9fcdb304dcd52f`。
- 既有 ExternalData store/generate/CMake 定向验证分别为 12/12、8/8、2/2；空覆盖回落到默认 store，non-runnable 显式覆盖保持隔离，错误父目录仍以 code 1 且无 URL 模板 fail closed。
- endpoint `10.62.215.229:2222` 的 r32 完整 W3 单次 launch 返回 target RC0，terminal/release/two clean scans 均为 PASS；terminal summary SHA256：`e20cd358d3ef3a3b5e62ceb1834d26911bebdf910976ed2e81f52faf3a3850d0`。
- 独立 W4：P0/P1/P2/P3=`0/0/0/0`。
- 禁止上传 Conan/CNB/其他制品仓；本 PR 只提交 recipe、补丁、报告和知识草稿。

---

## 补充说明

- **关联 Issue**：#2201
- **队伍名称**：天天开心
- **申请人显示标识**：2301_80739235
- **源分支**：2301_80739235:feat/itk-5.4.6
- **目标分支**：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- **其他说明**：四个知识目录查重结论为 `NO_EQUIVALENT_REUSABLE_KNOWLEDGE`。E265-E273 覆盖未知 CMake 系统的正向 WIN32/POSIX 能力选择、NEON 源集、NIFTI 数学库空绑定、冻结并真实导出 KWStyle/ExternalData 输入、可选 pthread cancellation API、CMake procfs 内存发现和 wrapper/controller/tree 四方绑定；E270 进一步记录 clean Conan worker 的 manifest-bound CID 导出、文本 PR diff 下的 canonical Base64 运输与解码校验、runnable 默认对象根、link/extra/duplicate fail-closed 和无 URL fallback，适用条件、反例、验证方式和边界均写入同 stem KV/Markdown 草稿。
