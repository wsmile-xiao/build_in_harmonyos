# E1000: Header-only Conan 包的接口目标与上游构建标志隔离

## 问题现象

header-only 库在包阶段没有二进制链接动作，但 consumer 仍可能在
`find_package`、目标解析或编译阶段失败。上游 Makefile 还常带
`-march=native` 等仅适用于构建机的参数，直接复用到 OHOS consumer 会破坏
交叉编译的可移植性。

## 根因

头文件包若只复制文件而不声明 `includedirs`、空的 `libdirs`/`libs` 和稳定的
CMake interface target，CMakeDeps 无法产生可消费的目标。与此同时，
`-march=native` 依赖宿主 CPU，不是目标平台能力；它与 Conan profile/toolchain
的编译器和架构绑定冲突。

## 修复步骤

1. 在生产配方中声明 `package_type = "header-library"`，仅复制公开头文件和
   许可证，并把 `cpp_info.includedirs` 绑定到包内 `include`。
2. 显式清空 `libdirs`、`bindirs`、`libs`，设置 `cmake_file_name` 与
   `cmake_target_name`，使 CMakeDeps 生成稳定的 interface target。
3. 用 CMakeDeps/CMakeToolchain 构建真实 consumer；测试程序必须调用被测库的
   类型、访问器或异常 API，`test()` 保留显式 `self.run(..., env="conanrun")`。
4. 将上游 `-march=native`、宿主路径和其他本地优化留在上游测试记录中，交叉
   recipe 只接受 Conan profile/toolchain 提供的目标参数。

## 验证方式

Mapbox Variant 1.2.0 的本地 `conan create` 成功打包 6 个头文件和 2 个许可
文件；CMake consumer 通过 `mapbox::variant` 目标编译并执行 7 项 API 断言。
上游 `make -j2 test` 的 90 个 Catch 用例（654 个断言）全部通过，7 个预期
编译失败用例全部通过，合并入口日志为 `2/2 PASS`。

## 适用范围与安全边界

该模式适用于不生成库文件、由 CMake/Conan 分发的 C/C++ 头文件库。若项目有
真实二进制、生成代码、运行时插件或平台专用 ABI，必须追加对应的库/运行时
闭包和目标验证，不能仅凭 header-only 规则宣称适配完成。

## 失败尝试

把上游的宿主优化参数直接写入 recipe，或让 consumer 只打印固定文本，都不能
证明目标接口可用；前者会导致交叉编译不可复现，后者会绕过被测包依赖并在
平台 L0/L1 破坏性测试中失败。
