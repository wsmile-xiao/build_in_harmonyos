## PR 信息
- **三方库名称**：nettle
- **上游版本**：4.0
- **上游仓库地址**：https://ftp.gnu.org/gnu/nettle/
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 117 | 上游 make check 测试套件 (AES/DES/ChaCha/SHA/HMAC/RSA/ECDSA/Ed25519等) |
| 集成测试 | 2 | test_package (SHA256+AES-128 消费者断言) |
| 其他测试 | 0 | 跳过的测试 |
| **合计** | **119** | |

### 是否存在对上游测试用例的修改？
否，补丁仅修改平台检测和 umask，不涉及测试代码

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 117 | 一致 | 全部通过 117/117 |
| 集成测试 | 2 | 一致 | test_package: SHA256+AES-128 PASS |
| 鸿蒙特有测试 | 0 | - | - |
| **合计** | **119** | | |

---

## 上游测试用例修改说明
- patches/0001-config.guess.patch: HarmonyOS aarch64 识别
- patches/0002-config.sub.patch: ohos-linux 映射
- patches/0003-configure.patch: umask 077→022

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: autotools
- 配置选项: `默认配置`

### 产物验证
| 编译无错误 | PASS | 构建系统: autotools, 状态: built |
| 产物存在性 | PASS | conan create 验证 |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | 通过: 119, 失败: 0, 跳过: 0 |
| 动态依赖 | PASS | 依赖: gmp/6.3.0 |

### 补丁说明
- `0001-config.guess.patch`: 0001-config.guess.patch
- `0002-config.sub.patch`: 0002-config.sub.patch
- `0003-configure.patch`: 0003-configure.patch

### 依赖
- gmp/6.3.0

### 测试结论
- 总体评价: 通过
- 已知限制: 无

### 遇到的问题与解决方案
- **1**: 根因=config.guess 不识别 HarmonyOS, 解决方案=E007
- **2**: 根因=configure umask 077 在 hmdfs 上失败, 解决方案=E011
- **3**: 根因=--with-include-path 不被识别, 解决方案=nettle 4.0 API 变更
- **4**: 根因=sha256_digest 参数数量变更, 解决方案=nettle 4.0 API 变更

### 验证命令
```
- conan create: PASS (G0-G4 全部通过)
- W3 本地 CI 模拟: PASS
- test_package: SHA256('abc') + AES-128 block encryption PASS
- 上游 make check: 117/117 tests passed
```
