# DRAFT-ea-submodule-commoncppflags-remove：EA 系库 release tar 缺 submodule 内共享 CMake 模块时移除 include

## 现象

EA 系库（EAMain 0.0.0-24ca8bf、EAStdC/eastdc 0.0.0-fbcc34e 等）顶层 `CMakeLists.txt` 通过
`CMAKE_MODULE_PATH` 指向 `test/packages/<dep>/scripts/CMake` 后执行 `include(CommonCppFlags)`。
该模块只存在于 git submodule 检出时；官方 codeload release tar **不含** `test/packages`
子模块内容。干净源码树 configure 阶段直接报：

```
CMake Error at CMakeLists.txt:16 (include): could not find requested file: CommonCppFlags
```

## 根因

- 上游把共享编译标志模块（CommonCppFlags）放在测试脚手架 submodule 内，发布归档不包含 submodule；
- `CommonCppFlags` 只设置编译标志（等价项由 Conan toolchain / 编译器默认提供），删除引用不改变构建语义；
- E150 的 manual-download 方案（另行下载 submodule）会引入未锁定、非确定性的网络依赖，此场景不需要。

## 可复用处理

1. 核对官方 release tar 是否真含被引用的 CMake 模块（`tar tzf <tarball> | grep CommonCppFlags`）；不含即确认缺失。
2. 判断被删模块是否仅提供编译标志/与 toolchain 重复；若是，直接以最小补丁删除 `set(CMAKE_MODULE_PATH ...)` 与 `include(CommonCppFlags)` 两行。
3. 等价标志由 Conan CMakeToolchain 提供（交叉工具链 + 依赖 include 注入，见 eastdc/eamain 配方 generate()）。
4. 用 `conan create`（host=ohos-aarch64）+ test_package 消费者真实编译链接运行验证。

## 证据

- eamain 0.0.0-24ca8bf：补丁 `0001-remove-submodule-commoncppflags.patch`，conan create EXIT:0（2026-09-19，R02），libEAMain.a 构建成功，test_package 1/1 Passed；
- eastdc 0.0.0-fbcc34e：同款补丁 `0002-guard-commoncppflags-include.patch` 已发布（R02 PR #10768，conan create 实测）；
- 两个独立库以同一方案通过，证明跨库可复用。

## 边界与反例

- 若缺失模块不是纯编译标志（含自定义安装宏/目标定义），不能直接删除，须走 fallback（锁定 vendor 或改 find）；
- 不适用于 submodule 内容是业务源码（非脚本/CMake 模块）的库；
- 不得把"本地存在 submodule 检出"误当 release 内容；必须以官方 tarball 为准。
