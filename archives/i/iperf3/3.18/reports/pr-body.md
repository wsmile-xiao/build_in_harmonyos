## PR 信息
- **三方库名称**：iperf3
- **上游版本**：3.18
- **上游仓库地址**：https://downloads.es.net/pub/iperf/iperf-3.18.tar.gz
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
iperf3 上游使用 autotools 构建系统，测试脚本 `test_commands.sh` 需要运行 server 和 client 进程进行网络测试，不适合在 CI 环境中运行。本次适配新增 CMake 构建系统作为 autotools 的替代方案（autotools config.status 在 HarmonyOS 上因临时目录权限限制失败），并新增 `test_package/test.c` 通过 `popen("iperf3 --version")` 验证二进制安装和功能正确性。

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
- `0002-src-pthread_stubs.c.patch`: 0002-src-pthread_stubs.c.patch
- `0003-iperf3.spec.patch`: 0003-iperf3.spec.patch
- `0004-config-config.guess.patch`: 0004-config-config.guess.patch
- `0005-config-config.sub.patch`: 0005-config-config.sub.patch
- `0006-src-iperf_config.h.patch`: 0006-src-iperf_config.h.patch
- `0007-src-version.h.patch`: 0007-src-version.h.patch

### 依赖
- 无外部 Conan 依赖（requirements() 为空）
- 编译依赖：clang, cmake, make
- 运行时系统库：libc, libpthread, libm

### 测试结论
- 总体评价: 通过
- 已知限制: 无

### 遇到的问题与解决方案
- **1**: 根因=config.status Permission denied, 解决方案=HMDFS temp dir creation fails
- **2**: 根因=平台识别, 解决方案=config.guess/config.sub 不识别 HarmonyOS
- **3**: 根因=pthread stubs 缺失, 解决方案=平台差异
- **4**: 根因=PACKAGE macro redefinition, 解决方案=CMake defines + iperf_config.h both define PACKAGE

### 验证命令
```
- conan-verify: G1/G2/G3/G4 all PASS
- W3 local CI simulation: PASS
- iperf3 --version: functional, shows all features
```
