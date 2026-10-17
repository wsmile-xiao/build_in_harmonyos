## PR 信息
- **三方库名称**：ldns
- **上游版本**：1.9.0
- **上游仓库地址**：https://www.nlnetlabs.nl/downloads/ldns/ldns-1.9.0.tar.gz
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游测试套件 |
| 集成测试 | 0 | - |
| 其他测试 | 0 | 跳过的测试 |
| **合计** | **0** | |

### 是否存在对上游测试用例的修改？
是，见下方补丁说明

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 一致 | 通过 0/0 |
| 集成测试 | 0 | - | - |
| 鸿蒙特有测试 | 0 | - | 新增 |
| **合计** | **0** | | |

---

## 上游测试用例修改说明
本次适配未修改任何上游测试用例。补丁仅涉及平台适配代码：
- `0001-config.guess.patch`: 在 config.guess 中添加 aarch64:HarmonyOS 平台检测
- `0002-config.sub.patch`: 在 config.sub 中添加 harmonyos-* 到 OS 和内核验证列表
- `configure` 脚本中的 config.status 临时目录创建逻辑通过 `replace_in_file()` 在 `build()` 方法中修复（非补丁方式，因为 configure 是源文件而非生成文件）
ldns 上游无标准 `make check` 测试目标，test_package 使用消费者视角验证（调用 ldns_rr_list_new/ldns_pkt_new/ldns_version API）。

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: autotools
- 配置选项: `默认配置`

### 产物验证
| 编译无错误 | PASS | 构建系统: autotools, 状态: published |
| 产物存在性 | PASS | conan create 验证通过 |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | 通过: 0, 失败: 0, 跳过: 0 |
| 动态依赖 | PASS | 依赖: openssl/3.5.6 |

### 补丁说明
- `0001-config.guess.patch`: 0001-config.guess.patch
- `0002-config.sub.patch`: 0002-config.sub.patch

### 依赖
- openssl/3.5.6

### 测试结论
- 总体评价: 通过
- 已知限制: 无

### 遇到的问题与解决方案
无已知问题

### 验证命令
```
- conan-verify G0-G4 + L2/L4/L5 全部通过
- 可标记 status: published
---
编译结束: 2026-08-10
---
**编译结束**: 2026-08-11 01:49
**最终状态**: published
```
