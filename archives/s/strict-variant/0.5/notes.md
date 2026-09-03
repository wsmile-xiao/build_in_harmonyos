# strict-variant 0.5 适配笔记

## 编译环境

- 目标：HarmonyOS PC arm64 / Conan `os=OHOS`, `arch=armv8`
- 编译器：`/data/service/hnp/bin/clang++` 15.0.4
- Conan：2.29.1；CMake：4.1.2
- 日期：2026-09-03
- 状态：built（本地 Conan 构建及消费者运行验证已完成；release upload 尚未确认）

## 源码与配方策略

- 来源为官方 GitHub tag `v0.5`，SHA-256 为
  `6bbb7add1323b8a298b2e264e22063abcbb2eb30e68afcccd6e95e88dea68ce0`。
- 该版本没有需要编译的库产物，完整公开头文件安装到
  `include/strict_variant/`，许可证安装到 `licenses/`。
- 归档包含 `bench/eggs-variant/CMakeLists.txt`。自动初始化工具先选中了这个
  无关的嵌套 benchmark；实际配方固定使用顶层 `include/` 和顶层 `test/`，没有
  把 benchmark 当成 strict-variant 构建系统。
- 上游 `include/strict_variant/version.hpp` 在 `v0.5` 归档中仍携带
  `0.4.0` 宏值；这是上游归档内容，配方版本按任务指定的官方 tag `0.5` 保持。

## 上游测试

官方入口 `bash test/run_tests.sh` 的实际失败为：

```text
Require b2 or bjam but it was not found. Aborting.
```

这是设备未安装上游 Boost.Build 执行器的明确工具限制，不是测试失败结论。根据
`test/Jamroot.jam` 直接使用相同的 C++11、`-Wall -Wextra -Werror -pedantic` 和
`STRICT_VARIANT_DEBUG` 参数编译并运行了 4 个 harness 目标及 2 个 tutorial 目标，
结果为 6/6 PASS、32 个注册单元用例全部通过。完整手工验证日志位于设备任务目录
`/storage/Users/currentUser/builds/strict-variant-0.5-upstream-manual.hm4W3p/result.log`。

首次严格 `-Werror` 编译时发现两项 Clang 15 诊断，均有源码定位：

1. `test/variant.cpp:1035`、`:1049` 使用的本地类型 `D` 只有用户拷贝构造，
   触发 `variant.hpp:148` 递归包装赋值实例化的
   `deprecated-copy-with-user-provided-copy`。
2. `test/tutorial_basic.cpp:156` 的演示 formatter 分支没有返回值，触发
   `return-type`。

配方只在 Clang 下对这两个诊断使用 `-Wno-error=...`，仍保留其他 `-Werror`，未
   修改上游源码、测试注册项或断言。修正后的设备结果为 6/6 PASS。

`spirit.cpp` 是上游显式条件测试。设备不存在 `/usr/include/boost/version.hpp`，
因此按 `Jamroot.jam` 的条件不注册该目标；这是 OHOS 设备缺少可选 Boost 头文件的
有据跳过，不把它伪报成 PASS，也不从清单分母删除。

## W0 依赖检查

上游 README 声明库本身无外部依赖。对 `ohpcd` 的配方查询命令因设备返回
`error:system acceleration policy not enabled` 而被策略拦截；这只能说明当前
注册表探测受设备策略限制，不能据此声称版本已发布或缺失。`init-build` 依赖预检
显示无需外部依赖。

## 消费者验证

`test_package` 使用 Conan CMakeDeps/CMakeToolchain 发现并链接
`strict_variant::strict_variant`，真实调用 default construction、assignment、
type/index get、`apply_visitor` 和 `emplace`，共 8 个断言，运行 1/1 PASS。

## 补丁与注意事项

无源码补丁。构建过程只对 Clang 15 的两个已定位上游测试警告降级；未知诊断仍会
使构建失败。知识沉淀候选为“自动源码探测误选嵌套 benchmark 时，header-only
库应按顶层公开头文件和上游测试入口固定打包/验证”，并附带可复用的上游测试
条件跳过及分母统计规则。
---

**编译结束**: 2026-09-03 13:06
**最终状态**: built
