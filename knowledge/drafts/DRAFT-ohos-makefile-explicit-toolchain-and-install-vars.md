# DRAFT-ohos-makefile-explicit-toolchain-and-install-vars：Makefile 依赖的 OHOS 工具链边界

## 现象

在 OpenHarmony PC 设备上，`silentbicycle/skiplist` 的上游 Makefile 默认使用 `cc` 和 `install`。设备的 Conan OHOS profile 明确提供 `/data/service/hnp/bin/clang`，但不会把该路径自动映射为 Makefile 的 `CC`；同样，设备可用的构建环境不保证存在独立的 GNU `install` 命令。首轮驱动因此在编译或安装阶段失败。

## 可复用处理

1. 在 Conan `build()` 中从 `tools.build:compiler_executables` 读取 C 编译器，并显式传入 `make CC=<profile compiler>`。
2. 不把缺失的 `install` 命令当作源码失败；对于库配方，直接在 `package()` 使用 Conan `copy()` 从已验证的构建产物和公开头文件建立包边界。
3. 上游自测仍用同一显式 `CC` 执行，并在 test_package 中真实链接和运行 API consumer。
4. 若第二个 Makefile 项目复现该现象，应复用此规则并继续验证，不要修改设备全局 PATH 或伪造安装成功。

## 证据

- 首轮驱动：`make: cc: No such file or directory`，随后 `/data/service/hnp/bin/clang` 显式构建 skiplist 的上游测试通过。
- 首轮安装：`install: No such file or directory`；Conan `copy()` 打包 `libskiplist.a` 和公开头文件后 conan create/W3 通过。
