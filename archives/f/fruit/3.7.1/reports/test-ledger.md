# fruit 3.7.1 上游测试双口径台账

## 统计口径

- `source_declared_total`：官方 tag v3.7.1 源码 `tests/test_*.py` 中按可复制枚举规则（`def test_` 方法计数）发现的测试声明总数 = **336**（31 个文件）。
- `configured_executable_total`：当前 OHOS 配置（CMake Release + clang15/libc++，`FRUIT_USES_BOOST=OFF`）实际由 pytest 收集实例化的独立可执行用例数 = **1201**（上游 `@parameterized.parameters` 参数化展开；每个 def test_ 方法展开为多个参数化用例）。
- `executed_passed_total` = **1201**，失败 = **0**，未运行/未实例化 = **0**。

通过率：`executed_passed_total / configured_executable_total = 1201/1201 (100%)`；
`configured_executable_total / source_declared_total` 超出 1.0 是因为参数化展开（336 个声明 → 1201 个实例），按任务要求保留源码声明总数并逐项说明原因（参数化宏展开，非互斥分支）。

## 逐文件映射（源码声明 → pytest 收集 → 实际执行）

| 测试文件 | 源码声明(def test_) | pytest 收集(参数化展开) | 执行 | 通过 | 结果 |
|---|---|---|---|---|---|
| test_bind_interface.py | 11 | 30 | 30 | 30 | pass |
| test_binding_clash.py | 8 | 89 | 89 | 89 | pass |
| test_binding_compression.py | 3 | 5 | 5 | 5 | pass |
| test_class_destruction.py | 2 | 4 | 4 | 4 | pass |
| test_component.py | 6 | 16 | 16 | 16 | pass |
| test_component_and_injector_params.py | 18 | 117 | 117 | 117 | pass |
| test_component_functions.py | 15 | 15 | 15 | 15 | pass |
| test_component_replacement.py | 23 | 71 | 71 | 71 | pass |
| test_defn_h_includes.py | 1 | 1 | 1 | 1 | pass |
| test_dependency_loop.py | 5 | 7 | 7 | 7 | pass |
| test_eager_injection.py | 2 | 2 | 2 | 2 | pass |
| test_include_test.py | 1 | 7 | 7 | 7 | pass |
| test_injected_provider.py | 9 | 40 | 40 | 40 | pass |
| test_injector.py | 11 | 46 | 46 | 46 | pass |
| test_injector_unsafe_get.py | 1 | 2 | 2 | 2 | pass |
| test_install.py | 29 | 45 | 45 | 45 | pass |
| test_install_component_functions.py | 11 | 11 | 11 | 11 | pass |
| test_misc.py | 1 | 1 | 1 | 1 | pass |
| test_multibindings_bind_instance.py | 7 | 19 | 19 | 19 | pass |
| test_multibindings_bind_interface.py | 6 | 14 | 14 | 14 | pass |
| test_multibindings_bind_provider.py | 18 | 130 | 130 | 130 | pass |
| test_multibindings_misc.py | 7 | 17 | 17 | 17 | pass |
| test_normalized_component.py | 6 | 12 | 12 | 12 | pass |
| test_register_constructor.py | 23 | 72 | 72 | 72 | pass |
| test_register_factory.py | 68 | 242 | 242 | 242 | pass |
| test_register_instance.py | 18 | 58 | 58 | 58 | pass |
| test_register_provider.py | 17 | 119 | 119 | 119 | pass |
| test_required_types.py | 6 | 6 | 6 | 6 | pass |
| test_semistatic_map_hash_selection.py | 1 | 1 | 1 | 1 | pass |
| test_type_alignment.py | 1 | 1 | 1 | 1 | pass |
| test_type_alignment_with_annotation.py | 1 | 1 | 1 | 1 | pass |
| **合计** | **336** | **1201** | **1201** | **1201** | **100%** |

## 执行方式

- 构建：`cmake .. -DCMAKE_BUILD_TYPE=Release -DFRUIT_ENABLE_CLANG_TIDY=FALSE -DFRUIT_TESTS_USE_PRECOMPILED_HEADERS=OFF -DFRUIT_USES_BOOST=False -DCMAKE_POLICY_VERSION_MINIMUM=3.5`（构建目录 `$HOME/tmp/builds/fruit-3.7.1.work/build-test`，CMake 生成 `tests/fruit_test_config.py` 指向已编译 libfruit）。
- 运行：`python3 -m pytest -p no:cacheprovider -r a -q <file>`，cwd = build-test/tests，CXX=clang++（OHOS aarch64），每个用例编译 C++ 片段 → 链接 libfruit → 实际运行。
- 完整原始日志：`reports/upstream-pytest.log`（逐文件 rc=0，全部通过）。
- 框架内部宏、SECTION 子节、样例（examples/）、基准（scaling_doubles）与 fixture 不误算为独立用例：上游用例仅统计用户测试源 `tests/test_*.py` 中的独立 pytest 用例；`tests/test_common.h/cpp`、`fruit_test_common.py`、`class_construction_tracker.h` 为测试框架/公共辅助，未计入。

## 消费者与鸿蒙专项（test_package，与上游测试分别计数）

| 用例 | 来源 | 调用公开 API | 结果 |
|---|---|---|---|
| test_fruit.cpp（消费者探针） | test_package | fruit::createComponent/bind/Injector::get<Greeter*> + 单例断言 | 编译+链接+运行通过（`fruit consumer OK`） |
| test_fruit_ohos.cpp（鸿蒙专项） | test_package | Annotated 注解注入 / get<Value&> / 单例断言（typeid/RTTI 类型键） | 编译+链接+运行通过（`fruit OHOS test OK: annotated=42 plain=7`） |

- 消费者用例仅通过已安装公开头文件 `fruit/fruit.h`、公开 API、`-lfruit` 链接目标与运行时产物使用该库；未包含库私有头文件、未复用库内部测试构建目录、非空壳（实际调用公开 DI API 并断言可观察结果）。
- 鸿蒙专项测试在 OHOS aarch64（clang15/libc++）真实编译运行，覆盖 multibindings 注解注入与 RTTI 类型键，非空壳/非伪造输出。
