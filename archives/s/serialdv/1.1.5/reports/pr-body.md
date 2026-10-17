- **三方库名称**：serialdv
- **上游版本**：v1.1.5
- **上游仓库地址**：https://github.com/f4exb/serialDV
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent 技能库（SKILL.md v12.22 + iron-rules R1-R52；参考知识条目 E274（SONAME 缺失）/E019（RPATH/LD_LIBRARY_PATH））

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：源包无 tests/ 目录，CMakeLists.txt 无 enable_testing()/include(CTest)/add_test() |
| 集成测试 | 0 | 上游唯一测试性产物为 dvtest 工具，运行需真实 AMBE3000（ThumbDV 串口）或 AMBE-over-UDP 服务端 |
| 其他测试 | 0 | samples/*.raw 仅为 8 kS/s S16LE 输入样本，非断言型用例 |
| **合计** | **0** | 清点证据见 `test_package/MANIFEST.yml`（R51） |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试（消费者 API 回归） | 59 断言 | 新增 | `test_package/test_serialdv.cpp`，`conan create` 自动执行（协议常量/MBE 帧长位数全速率矩阵/生命周期/串口与 UDP 错误路径/Dummy 契约） |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| 鸿蒙特有测试（PC 特有/设备侧消费者 E2E） | 11 断言 | 新增 | HarmonyOS PC 真机上链接包内 `libserialdv.so`，经 OHOS UDP/串口接口对模拟 AMBE3000 服务端完成 PRODID 握手/速率切换/encode(9B+18B)/decode(192 样本) 全链路（真机证据见 `reports/test-report.md`） |
| **合计** | **70 断言** | **+70** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：消费者视角补全 59 条断言（协议常量、`getNbMbeBytes`/`getNbMbeBits` 全速率矩阵、关闭态拒绝 encode/decode、非 TTY 串口与 UDP 非法入参错误路径、DummyDataController 契约）；鸿蒙特有测试（PC 真机）补全 11 条协议端到端断言（在 HarmonyOS PC 上链接包内 `libserialdv.so`，经 OHOS UDP/串口接口对模拟 AMBE3000 服务端验证 PRODID/速率/编码/解码全链路与确定性载荷回读）
> - **补全原因**：上游无自动化测试套件（无 tests/ 目录、无 ctest 注册），唯一测试性产物 dvtest 需真实 AMBE3000 硬件，CI 环境无此硬件
> - **新增测试文件清单**：
>   1. `archives/s/serialdv/1.1.5/test_package/test_serialdv.cpp` — 消费者 API 回归测试（59 断言，随包提交）
>   2. （设备验证用，不随包提交）`serialdv_udp_e2e.cpp` — 模拟 AMBE3000 服务端协议 E2E 验证程序，证据见 `reports/test-report.md`

## 验证结果

- 编译状态：通过（同一配方经 `conan-verify` G2、本地 CI 门禁、`finish` W3 三次干净 `conan create`）
- 上游测试用例通过率：0/0（上游无测试套件；清点证据见 `test_package/MANIFEST.yml`）
- 新增测试用例通过率：59/59（100%）；鸿蒙特有测试（PC 真机协议 E2E）11/11（100%，复跑 2 次）

## 补充说明

- 零补丁适配：OHOS SDK sysroot 已提供 `linux/serial.h`（struct serial_struct）、`TIOCGSERIAL/TIOCSSERIAL`、`ASYNC_LOW_LATENCY`、`B230400/B460800`；配方 `generate()` 注入 `-Wl,-soname,libserialdv.so` 修复 OHOS CMake 平台无 SONAME（CI L5a）问题（参考仓库内 apache-arrow/boost 同类适配先例）。
- 本地 CI 门禁（与平台 CI 同源脚本）结果：G0/KC/JC/L0/L1/L4/L5 PASS；L2 为非阻塞跳过（`dvtest --version` 需 `LD_LIBRARY_PATH`，原因为 OHOS CMake 不写 RPATH；库消费者由 Conan 生成器接管链接参数，`test_package` 59/59 通过）。
- W4 独立审计：verdict=pass，P0=0/P1=0（2 项 P2 规范建议保留、1 项 P3 文档描述已修复），详见 `reports/audit-result.json`。
- 已知限制：实际编解码功能需要 AMBE3000 硬件（ThumbDV 串口）或 AMBE-over-UDP 服务端；上游 `getNbMbeBytes/getNbMbeBits` 未覆盖 `DVRate7100x4400`/`DVRate2400`（返回 0，已以行为断言如实记录）。
