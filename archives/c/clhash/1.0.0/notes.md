# clhash 1.0.0 适配记录

## W0/W0b

- 任务 #7261 为无依赖 C 依赖项；`preflight_check.sh clhash/1.0.0` 检查通过。
- 上游官方仓库已从 `lemire/clhash` 重定向到 `simdhash/clhash`；使用官方 tag tarball：
  `https://github.com/lemire/clhash/archive/refs/tags/v1.0.0.tar.gz`。
- SHA-256：`fcf9549fad7c1487b7164e49faf043f85831a7b706a660edfc5bb1bc7ffedfcf`。
- 语言预检：任务声明 `c`，构建系统识别为 CMake，源码含 C/C++ 测试；预检判定为兼容族 `cpp`，不是语言阻塞。
- 预扫描命中 0 条风险；构建系统同时包含 CMake 和 Makefile，主配方选择上游 CMake 安装规则。

## 适配与测试

- `conanfile.py` 使用 `CMakeToolchain` 和 `cmake_layout`，默认 `BUILD_SHARED_LIBS=OFF`；无外部依赖。
- `package()` 使用上游 CMake install，交付静态库、公共头文件、CMake package config，并复制 Apache-2.0 LICENSE。
- `build()` 调用 `cmake.test()`，执行官方 CTest：`clhash_unit` 与 `clhash_cppunit`，设备实测 2/2 通过。
- 另按上游 Makefile 入口实测 `make -j1`，运行 `unit`、`cppunit`、`example`、`cppexample`，4/4 通过；Makefile 使用 AArch64 `-march=armv8-a+crypto`。
- `test_package` 构建两个 CMake 消费者并真实链接 `clhash::clhash`：`test_clhash.c` 调用 key 生成、已知答案、确定性、输入敏感性、空输入、位翻转恢复和版本宏，共 8 项检查；`test_ohos.c` 在 HarmonyOS 运行时校验 uname 身份并调用 clhash，共 4 项检查；合计 2 个消费者程序、12 项检查，均通过。

## CI 反馈与修复

- 首次 PR #9626 的远程 CI #44687 在 CMake configure 阶段失败：上游无条件 include `cmake/CPM.cmake`，该引导文件在缓存缺失时从 GitHub 下载 CPM.cmake；CI worker 的外网下载失败。
- `CMakeLists.txt` 实际没有使用 `CPMAddPackage` 或任何 CPM API，因此从源码工作树移除该无用 include，并由 `refresh-patch --auto` 生成 `patches/0001-CMakeLists.txt.patch`。
- 该错误模式与既有 `DRAFT-glob-0.0.1-cmake-offline-install` 同类，已有知识覆盖，不重复创建路径 B 草稿或 Issue；本任务仍按路径 A 交付。
- 补丁重新应用后的 Conan G2/W3 必须验证，远程 CI #44687 的失败证据不会作为最终结果。

## 路径判断

- 本次是该库自身的 CMake/Conan 归档适配；没有形成可跨仓库复用的新知识，按路径 A 处理，不创建知识扩展 Issue。
- `conan-init` 因源码同时存在 Makefile/CMakeLists.txt 初次误选 Autotools；已在当前归档内校正为 CMake 配方，未修改框架脚本。

## 交付物

| 文件 | 说明 |
|---|---|
| `lib/libclhash.a` | OHOS AArch64 静态库 |
| `include/clhash.h` | 公共 C/C++ 头文件 |
| `lib/cmake/clhash/` | CMake package config/targets |

## 结束

最终状态: built（等待 PR CI 验证）
