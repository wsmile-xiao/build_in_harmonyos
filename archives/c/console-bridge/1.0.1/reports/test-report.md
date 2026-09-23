# console-bridge 1.0.1 测试报告

## 测试清点

| 测试层 | 数量 | 内容 |
| --- | ---: | --- |
| 上游 GoogleTest | 13 | 日志宏、格式化、级别过滤、输出处理器与文件输出 |
| 上游 CTest | 1 | `console_TEST`，承载上述 13 个用例 |
| 可选 lint | 2 | cppcheck/cpplint；依赖 wget 联网下载脚本，不属于离线功能测试 |
| Conan test_package | 9 | 消费者视角真实 API 行为断言 |

## 实际结果

### 原始上游基线（macOS arm64）

- 配置：CMake 4.4.3、Apple Clang 17、Release、`BUILD_TESTING=ON`
- CTest：1/1 通过
- GoogleTest：13/13 用例通过
- lint：未注册，因为环境中没有 wget

### Conan 配方预验证（macOS arm64）

- 动态库默认配置：`conan create` 通过
- 静态库 `shared=False`：`conan create` 通过
- 内嵌上游 CTest：1/1 通过（13/13 GoogleTest 用例）
- `test_package`：通过（9 项真实行为断言）
- 产物：动态/静态 `libconsole_bridge`、公开头文件、CMake config、pkg-config 文件

## HarmonyOS PC 状态

当前工作机不是 HarmonyOS PC，因此未把以上 macOS 结果标记为 W3。HarmonyOS PC 的 `conan create`、ELF/SONAME、安全扫描和运行结果必须以远端 worker/CI 实测为准。
