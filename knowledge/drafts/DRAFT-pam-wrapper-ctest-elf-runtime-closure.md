# OHOS CTest 构建树 ELF 运行闭包签名

> 来源：pam-wrapper 1.1.8，PR 4234
> 状态：DRAFT

## 现象

Conan 配方可以完成 CMake 编译，但在 `build()` 中直接执行 CTest 时，测试
可执行文件或其动态加载对象报 `Permission denied`、`Operation not permitted`
或 `dlopen` 失败。即使 `package()` 会签名最终 `.so`，上游测试仍可能失败。

## 根因

Conan 的阶段顺序是 `build()` 先于 `package()`。CTest 消费的是构建树，而不是
稍后生成的 package folder，因此打包阶段签名不会回溯修复 CTest 的输入。

动态测试还存在一个容易遗漏的运行闭包：

- CTest 启动的测试可执行文件；
- 测试直接链接的共享库；
- `LD_PRELOAD` 指定的插桩或拦截库；
- 运行时通过 `dlopen` 加载的 MODULE、PAM 模块或插件。

只签名测试入口仍会在后续加载未签名对象时失败。该问题与 E077 的区别是：
E077 处理安装后修改 ELF 的重签名顺序，本条目处理 `package()` 尚未开始时的
构建树测试闭包。

## 推荐方案

1. 在 `cmake.build()` 之后、`ctest` 之前枚举测试入口及其加载对象。
2. 只处理普通 ELF 文件，跳过目录、符号链接和非 ELF 数据。
3. 对每个 ELF 先移除旧 `.codesign`，再用同一签名工具重新签名。
4. 签名工具缺失或任一签名失败时立即终止，不能静默关闭上游测试。
5. 为测试创建私有可写 `TMPDIR`，随后运行 `ctest -N` 和完整 verbose CTest。

pam-wrapper 的闭包包括 `test_pam_wrapper`、`pam_wrapper`、`pamtest` 以及
`pam_matrix` 等测试 PAM 模块。配方在 CTest 前统一处理这些 ELF，随后在
aarch64 OHOS 6.0 设备上通过 1/1 CTest 目标和 23/23 CMocka 用例。

## 验证证据

- 运行目录：`/storage/Users/currentUser/ohos-test-runs/codex-pam-wrapper-upstream-20260807-144624`
- CTest 日志 SHA256：`9660199e69663db0bcced0d4bf802d3d6e318219030ecad4e731bd7806c9ed87`
- 结果：CTest 1/1、CMocka 23/23、Conan consumer authentication test 通过。

## 禁止做法

- 只在 `package()` 中签名后声称覆盖了 build-tree CTest。
- 只签测试可执行文件，遗漏 preload 库、共享库或插件。
- 用 `ctest || true`、`ignore_errors` 或默认关闭测试掩盖签名失败。
- 对 `Permission denied` 反复 `chmod`；签名问题不由 Unix mode 位解决。
