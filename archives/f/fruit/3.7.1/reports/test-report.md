# fruit 3.7.1 测试报告

## 测试环境

- 平台：HarmonyOS PC (aarch64)，os=OHOS 6.0，compiler=clang 15.0.4，libc++17，Release
- 构建：CMake 4.1.2 + Conan 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 源码：google/fruit v3.7.1（SHA-256 `ed4c6b7ebfbf75e14a74e21eb74ce2703b8485bfc9e660b1c36fb7fe363172d0`）

## 上游测试（双口径）

- 源码声明总数（`def test_` 方法枚举）：**336**（31 个 `tests/test_*.py`）
- 当前配置 pytest 收集实例化（含参数化展开）：**1201**
- 实际执行并通过：**1201**，失败 0，未运行 0 → `1201/1201 (100%)`
- 完整逐文件映射见 `reports/test-ledger.md`，原始日志 `reports/upstream-pytest.log`

## 鸿蒙专项测试（test_package）

- `test_fruit.cpp`（消费者探针）：fruit::createComponent/bind/Injector::get<Greeter*> + 单例断言 → 编译/链接/运行通过（`fruit consumer OK`）
- `test_fruit_ohos.cpp`（鸿蒙专项）：Annotated 注解注入 / get<Value&> / RTTI 类型键 / 单例语义 → 编译/链接/运行通过（`fruit OHOS test OK: annotated=42 plain=7`）
- 命令：`clang++ -std=c++11 <test>.cpp -o <probe> -I<include> -L<lib> -lfruit && ./<probe>`（OHOS aarch64 原生运行）

## 构建验证

- `conan create . --version=3.7.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`：exit 0，库本体 + test_package 全部通过（详见 `reports/conan-create.log`）
- conan-verify G1-G4 全部 PASS；W3 本地 CI 模拟（setup.sh + build_and_test.sh）通过

## 结论

fruit 3.7.1 在 OHOS aarch64 上完整适配验证通过：库可编译、可链接、可运行，上游测试全量通过，消费者与鸿蒙专项测试真实执行通过。
