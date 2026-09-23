# variant-lite 3.0.0 适配笔记

## 编译环境

- 构建系统：CMake 3.x，Conan 2.29.1
- 编译日期：2026-09-05
- 目标 profile：`ci/conan/profiles/ohos-aarch64`（OHOS/aarch64，clang 15，libc++，Release）
- 状态：built（已通过本地 W3/conan-verify，尚未发布）

## 编译步骤

1. 使用上游 `v3.0.0` 源码归档，SHA256 为 `bd596550369f33ef9455566822f5a4d52852a63a33d3d70ac1fbb529b78abc7b`。
2. Conan recipe 使用 `CMakeToolchain`，在 OHOS 下将 CMake system name 映射为 Linux、processor 映射为 aarch64；开启 `VARIANT_LITE_OPT_BUILD_TESTS` 和 `VARIANT_LITE_OPT_SELECT_NONSTD`，关闭 examples。
3. `build()` 调用 `cmake.configure()`、`cmake.build()`、`cmake.test()`；`package()` 调用 `cmake.install()`。
4. 包类型为 Conan header-library，导出 CMake target `nonstd::variant-lite`，`cpp_info.libs` 为空。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `ohc-run build` Step5 报“安装无产物” | 框架的安装产物检查只统计 `bin/` 和 `lib*/*.so/a`，不识别纯头文件包 | 保留源码安装结果；按 header-library 语义使用 Conan 的 CMake package 检查，并由 W3/test_package 验证真实消费 |
| 2 | `ohc-run build --resume-from Step6` 的 Step7 执行 `make check` 失败 | 上游 CMake 工程没有 `check` 目标 | 配方使用 Conan CMake helper 的 `cmake.test()`，实际执行上游 CTest |

上述两项是当前 ohc-run 流程与该 CMake/header-only 工程的工具链交互问题，不是源码编译或测试失败；原始日志保留在设备 `~/make-check-62556.log`、`~/build-driver-variant-lite-3.0.0.log` 及本归档 `reports/`。

## 源码修改

无上游源码补丁。仅新增 Conan 2 配方、真实消费者 test_package、MANIFEST 和归档记录。

## 依赖版本

无第三方 Conan 依赖。

## 验证结果

```text
conan-verify variant-lite 3.0.0：PASS
上游静态 CASE 声明：93；其中 variant.t.cpp 86、variant-main.t.cpp 6 已被上游 CMake 注册，variant-override.t.cpp 1 未列入 SOURCES。
上游实际 CTest runner：4/4 通过（test-cpp98、test-cpp11、test-cpp14、test-cpp17）；对应已注册的 92 个 CASE 声明均被四种标准模式编译并执行。
未执行：1 个未被上游 CMake 注册的 variant-override.t.cpp CASE 声明。
test_package：1/1 消费者程序通过，执行 8 项 variant/get/index/holds_alternative/get_if/visit API 断言。
```

## 交付物

| 文件 | 说明 |
|------|------|
| `include/nonstd/variant.hpp` | 上游单头文件 |
| `lib/cmake/variant-lite/*.cmake` | 上游 CMake package 配置 |

## 注意事项

- 使用 `find_package(variant-lite CONFIG REQUIRED)` 和 `nonstd::variant-lite` target；不要把它当作带链接库文件的普通 library。
- 设备上的本地下载缓存仅用于本次验证，不进入提交，也不代表 CI worker 已共享该缓存。
---

**编译结束**: 2026-09-05 22:41
**最终状态**: built
