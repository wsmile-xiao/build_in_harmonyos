# CMake 上游未注册 CTest 时空套件返回成功，配方必须直接执行测试可执行文件

- **草稿 ID**: DRAFT-box2d-2.4.1-ctest-empty-suite-false-pass
- **来源**: Box2D 2.4.1 HarmonyOS PC 适配（上游单测未注册 CTest，配方在 build 阶段直接执行 unit_test 二进制）
- **分类**: build-system / cmake / conan / testing
- **状态**: 本地草稿（已挂 PR #8849，路径 B 知识库扩展申请中）

## 问题 / 错误签名

- **ctest 空套件假阳性**：在构建目录执行 `ctest` 输出 `No tests were found!!!` 且**退出码为 0**——依赖退出码或粗扫输出的配方/CI 会把"没有测试"误判为"测试通过"。
- **复现**：Box2D 2.4.1 构建完成后（`BOX2D_BUILD_UNIT_TESTS=ON`）构建树存在 `bin/unit_test` 可执行文件，但整个构建树无任何 `add_test()` 注册，`ctest` 永远找不到用例。
- **对照验证**：直接运行 `bin/unit_test`，doctest 输出 `test cases: 5 | 5 passed`、`assertions: 36 | 36 passed`；同目录 `ctest` 输出 `No tests were found!!!` 且 `$? == 0`。

## 根因

1. **上游测试机制与 CTest 无关**：Box2D 2.4.1 的单元测试用 doctest 框架编译为独立可执行文件 `unit_test`，上游 CMakeLists 从不调用 `enable_testing()`/`add_test()`；上游官方 CI（GitHub Actions）就是直接运行这个二进制，ctest 从未参与。

2. **ctest 空套词语义陷阱**：ctest 在没有任何注册测试时打印 `No tests were found!!!` 并返回成功。这是"无测试可跑"与"测试全部通过"在退出码上的不可区分问题，靠 `cmake.test(self)`（其内部调 ctest）无法发现。

3. **关联决策（同库另一条经验，非本条目范围）**：Box2D 的 testbed（图形演示）依赖 GLFW/OpenGL/imgui 图形栈，与核心物理引擎无关；配方以 `BOX2D_BUILD_TESTBED=OFF` 关闭 testbed、保留 `BOX2D_BUILD_UNIT_TESTS=ON`，把可无头运行的单测与图形演示解耦。

## 最小修复方案

在 `archives/b/box2d/2.4.1/conanfile.py` 范围内：

`build()` 在 `cmake.build()` 之后直接执行测试二进制（不要用 `cmake.test()`）：

```python
from conan.tools.build import cross_building

def build(self):
    cmake = CMake(self)
    cmake.configure()
    cmake.build()

    # Box2D registers no CTest tests; its official CI runs this executable.
    if not cross_building(self):
        executable = "unit_test.exe" if self.settings.os == "Windows" else "unit_test"
        configuration = (
            str(self.settings.build_type) if cmake.is_multi_configuration else ""
        )
        command = os.path.join(self.build_folder, "bin", configuration, executable)
        self.run(f'"{command}"')
```

要点：

- `cross_building(self)` 守卫：交叉编译（目标机无执行环境）时跳过，测试由真机侧消费者测试补位（test_package）。
- `is_multi_configuration` 分支：MSVC/Xcode 等多配置生成器下二进制位于 `bin/<build_type>/`，单配置（Ninja/Make）位于 `bin/`。
- Windows 下补 `.exe` 后缀。

回退方案（如必须走 ctest 路线）：为上游 CMakeLists 追加 `enable_testing()` + `add_test(NAME unit_test COMMAND $<TARGET_FILE:box2d_unit_test>)` 补丁并注册进配方 `patches`；补丁必须按 P005 保持可向上游提交。

## 验证结果

| 环境 | 结果 |
|------|------|
| Windows host · Conan 2.31.2 + MSVC 2022 + CMake 3.31.6 | `conan create --build=missing` 通过；unit_test 5/5 用例、36/36 断言通过 |
| HarmonyOS PC aarch64 真机 ×2 · Conan 2.29.1 + clang 15 + `ohos-aarch64`（jobs=1） | 单包 CI `Total: 1 / Success: 1 / 100.0%`；L1（含 L1e 破坏性负向测试）通过 |
| 消费者验证 | `test_package` 真机链接 `box2d::box2d` 静态库，创建静态/动态刚体并运行 60 步仿真，6 项断言全部通过 |

## 禁止策略

- 禁止用 `BOX2D_BUILD_UNIT_TESTS=OFF` 回避测试执行问题——那是删除质量证据，适配后测试对比将显示 -5，无法证明库在 HarmonyOS 上行为正确。
- 禁止对该上游调用 `cmake.test(self)`/`ctest`——空套件退出码 0 会把"从未执行"记录成"全部通过"。

## 相关

- 相似条目：E230（源码分发型传输库不能只验证编译宏矩阵——同属"编译通过 ≠ 行为验证"主题）
- 引用原则：P005（补丁必须可向上游提交，约束回退方案的 add_test 补丁）
