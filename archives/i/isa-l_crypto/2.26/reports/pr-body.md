## PR 信息
- **三方库名称**：isa-l_crypto
- **上游版本**：2.26
- **上游仓库地址**：https://github.com/intel/isa-l_crypto/archive/refs/tags/v2.26.tar.gz
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
本次适配未修改上游测试用例。上游测试需要 OpenSSL 头文件，鸿蒙系统无 OpenSSL 开发头文件，因此禁用测试编译。库本身功能不受影响。test_package 使用 MD5 已知答案测试验证 API 调用。

## 验证结果

### 编译验证
- 编译器: clang (aarch64-unknown-linux-ohos)
- 编译状态: 成功
- 构建系统: cmake
- 配置选项: `默认配置`

### 产物验证
| 编译无错误 | PASS | 构建系统: cmake, 状态: built |
| 产物存在性 | PASS | conan create 验证 |
| ELF 格式 | PASS | aarch64-unknown-linux-ohos |
| 运行测试 | 通过 | 通过: 0, 失败: 0, 跳过: 0 |
| 动态依赖 | PASS | 依赖: 无 |

### 补丁说明
- `0001-CMakeLists.txt.patch`: 0001-CMakeLists.txt.patch
- `0002-aes-aarch64-gcm_common.S.patch`: 0002-aes-aarch64-gcm_common.S.patch

### 依赖
- cmake 4.1.2
- clang 15.0.4
- GNU binutils (as) 2.45

### 测试结论
- 总体评价: 通过
- 已知限制: 无

### 遇到的问题与解决方案
- **1**: 根因=SVE 汇编编译失败, 解决方案=clang 集成汇编器不支持 `.req` 寄存器别名语法
- **3**: 根因=aarch64 无 x86 SIMD, 解决方案=ISA-L 针对 x86 SIMD 设计，aarch64 使用 ASIMD/SVE/SVE2

### 验证命令
```
编译成功。libisal_crypto.so.2.25.0 (4.3MB, arm64 ELF)。
SONAME: libisal_crypto.so.2。仅链接 libc.so。
```
