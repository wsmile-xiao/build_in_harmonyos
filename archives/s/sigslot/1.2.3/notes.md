# sigslot 1.2.3 适配记录

## 来源与依赖预检

- 官方来源：https://github.com/palacaze/sigslot，版本标签 `v1.2.3`，commit `b588b79`。
- 源码归档：`https://github.com/palacaze/sigslot/archive/refs/tags/v1.2.3.tar.gz`。
- 现场下载后 SHA-256：`36c30a88f05c8f8e6b4800d8f9c7c006cf61164695bf5fd91a8b80ed4e1d96af`。
- 上游是 C++14 header-only 库，公开头文件包括 `signal.hpp` 以及 Boost/Qt 可选适配头；本配方完整打包 `include/sigslot/` 下的 `.hpp` 文件。
- 官方 ConanCenter 1.2.3 配方确认没有第三方 Conan 依赖；上游 CMake 仅通过 `Threads::Threads` 使用系统 pthread。
- 设备端依赖预检命令：`conan download "sigslot/1.2.3" -r=ohpcd --only-recipe`。
- 该命令在设备端因远端返回 `error:system acceleration policy not enabled` 退出 1；这证明的是设备/远端策略限制，不是把依赖误判为“仓库不存在”。随后使用官方源码归档与本地配方继续验证。

## 配方设计

- 使用 `package_type = "header-library"`，清空 package ID，CMake 包名为 `PalSigslot`，消费者 target 为 `Pal::Sigslot`。
- Conan 构建显式打开 `SIGSLOT_COMPILE_TESTS`，并构建上游的 `sigslot-tests` 目标。该目标在上游 CMake 中为 `EXCLUDE_FROM_ALL`，不能只调用默认构建目标。
- HarmonyOS 的 CMake toolchain 映射为 `CMAKE_SYSTEM_NAME=Linux`、`CMAKE_SYSTEM_PROCESSOR=aarch64`；上游测试链接到设备提供的 `pthread`。
- `test_package` 覆盖 signal 发射、连接阻塞/恢复/断开、RAII connection、group 顺序、兼容参数 signal chaining、shared_ptr 跟踪失效，共 16 个检查。
- 没有生成补丁：本版本上游源码在设备端配置、编译、链接和测试均不需要修改，`patches_applied: []`。
- 该库是库包而非可执行软件，不新增 `commands.json`。

## 上游测试统计

上游 `test/` 中有 14 个 `.cpp` 候选测试。设备端 CMake 因 Boost 和 Qt 可选依赖未安装，只注册了 12 个测试：

| 项目 | 数量 | 结果 |
| --- | ---: | --- |
| 源码测试候选 | 14 | 12 注册，2 个有据跳过 |
| CTest 注册 | 12 | 全部执行 |
| CTest 通过 | 12 | 12/12，100% |
| CTest 失败 | 0 | 无 |
| 有据跳过 | 2 | `boost-tracking.cpp`、`qt-tracking.cpp` |

跳过证据为设备端 CMakeCache 中 `Boost_DIR=Boost_DIR-NOTFOUND`、`Qt5_DIR=Qt5_DIR-NOTFOUND`，且上游 `test/CMakeLists.txt` 只有在对应 imported target 存在时才注册这两个测试。跳过项没有计入通过数。

## 设备验证证据

- 设备工具：Conan 2.29.1、CMake 4.1.2、clang/clang++ 15.0.4。
- 独立上游测试日志：`$HOME/tmp/sigslot-1.2.3/upstream-test.log`，设备绝对路径为 `/storage/Users/currentUser/tmp/sigslot-1.2.3/upstream-test.log`。
- 测试注册摘要：`$HOME/tmp/sigslot-1.2.3/upstream-test-registration.log`。
- 上游结构核对：`$HOME/tmp/sigslot-1.2.3/upstream-structure.log`。
- 源码下载日志：`$HOME/tmp/sigslot-1.2.3/source-download.log`。
- 远端 recipe 预检日志：`$HOME/tmp/sigslot-1.2.3/w0-recipe.log`。
- 最终 Conan create 命令：`conan create archives/s/sigslot/1.2.3 --build=sigslot/* --test-folder test_package -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -c:a tools.build:jobs=1 -nr`。
- 最终 Conan create 日志：`$HOME/tmp/sigslot-1.2.3/conan-create-manifest-final.log`，退出码 0。
- test_package 最终 SHA 独立运行复核：`$HOME/tmp/sigslot-1.2.3/runtime-check-finalsha.log`，退出码 0。

最终设备构建中，12 个注册测试均完成编译并由 CTest 执行通过；主包和 test_package 的实际构建命令均显示 `--parallel 1 -- -j1`。CMake 配置曾报告 `/proc/meminfo` 解析 warning，但配置、链接和测试均成功，该 warning 不作为失败理由。

## 状态边界

- 本文件记录的是适配和设备验证证据；`test_package/MANIFEST.yml` 已补齐 CI L0e 所需的上游/消费者测试声明。
- 按用户要求，未运行 GitCode CI、AI Review、`ohc-run.py feedback`，也未修改 `SKILL.md`、references、templates、scripts、ci 或 knowledge 图谱。
