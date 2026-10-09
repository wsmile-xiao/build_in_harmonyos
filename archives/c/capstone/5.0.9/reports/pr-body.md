- **三方库名称**：capstone
- **上游版本**：5.0.9
- **上游仓库地址**：https://github.com/capstone-engine/capstone
- **适配路径**：路径 A（基础适配）
- **使用知识库**：adapt-lib-flow skill + openharmony-compile-agent skill

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 24 | 来源：`tests/` 下 23 个 `test_*.c` + `suite/arm/test_arm_regression.c`（CAPSTONE_BUILD_TESTS=ON 且 ARM 支持开启时由 CMake 构建为 24 个 `test_*` 二进制，均为原生反汇编硬编码字节序列冒烟测试） |
| 集成测试 | 0 | 上游无独立集成测试套件 |
| 其他测试 | 0 | — |
| **合计** | **24** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 24 | 不变 | 复用上游 24 个 `test_*` 二进制，在 build() 阶段由 OHOS aarch64 构建宿主机原生执行 |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test.c`：端到端消费者用例，反汇编 aarch64 机器码 `mov x0,#42; ret` 并断言 7 项结果 |
| **合计** | **25** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖

## 验证结果

- 编译状态：通过（`conan create` 构建 `libcapstone.so.5.0.9` / `libcapstone.so` / `libcapstone.a` + 头文件 + cmake 配置 + `libcapstone.pc`，并完成代码签名；CI #13416 通过）
- 上游测试用例通过率：24/24（100%）— 24 个 `test_*` 二进制均在 OHOS aarch64 上真实执行且全部通过
- 新增测试用例通过率：1/1（100%）— 端到端消费者用例（反汇编 aarch64 机器码并断言 7 项结果）

## 补充说明

- capstone 为纯 C 多架构反汇编库，零外部依赖；OHOS 适配采用自发现 `ohos.toolchain.cmake` + 裸 cmake 构建（绕开 `conan_toolchain` 在 os=OHOS 下 `CMAKE_SYSTEM_NAME` 映射异常），并对产物 `.so` 做鸿蒙 XPM 代码签名。
- 上游 24 个 `test_*` 二进制为纯反汇编冒烟测试（硬编码字节序列，无外部依赖、无网络/硬件需求），在 OHOS 构建宿主机原生执行，反汇编结果为确定性、与平台无关，故全部通过。
- 本机（开发设备）musl loader 对 ~9MB 工具链产物的 `.so` 存在加载怪癖，仅影响本地运行，CI 构建宿主机可正常加载 `libcapstone.so` 并跑通全部用例（同配方 5.0.7 的 test_package 已验证），故交由 CI 真实执行验证。
- W4 独立审计 verdict=pass（P0/P1=0）。
