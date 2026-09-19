# libcxx-serial 1.2.1 适配笔记

- 适配日期：2026-09-19；设备真机（OHOS arm64，/data/service/hnp 工具链）
- 平台任务：ohpcd id=13116，分支 feat/libcxx-serial-1.2.1，火种：开源鸿蒙PC专项积分赛

## 1. 上游识别

- 平台任务名 `libcxx-serial/1.2.1` 对应上游 **wjwwood/serial** tag `1.2.1`
  （Debian 源码包名即 libcxx-serial，RFS libcxx-serial/1.2.1-2 佐证："Serial Port library written in C++"）。
- 源码：https://github.com/wjwwood/serial/archive/refs/tags/1.2.1.tar.gz
- sha256：`0c2a789ce485a83ed640c777a7d1cd1256976890ece4c126f93751a08643917a`
- License：MIT（package.xml `<license>MIT</license>`；tarball 无单独 LICENSE 文件）。

## 2. 依赖（W0）

- 上游为纯 C++03/11 + POSIX（termios/ioctl/select/pthread-mutex/clock_gettime），
  **零外部依赖**。
- W0 实测（pipeline w0，私有 CONAN_HOME）：conan install
  --requires=libcxx-serial/1.2.1 --build=never → remotes 无此包，
  version_occupancy=missing（版本号可占用；本包为首次适配）。
- 上游测试（仅 test_package 消费者测试阶段使用，不进入库依赖闭包）：
  gtest/1.17.0.2 与 boost/1.91.0.1.3 的 OHOS 二进制均已实测可
  `conan install --build=never` 安装。

## 3. 适配点

1. **catkin 移除（patches/0001-plain-cmake-build.patch，整文件替换 CMakeLists.txt）**
   上游 `find_package(catkin REQUIRED)` 硬依赖 ROS catkin，非 ROS 环境不可配置。
   补丁改为纯 CMake：
   - 仅编 unix 实现路径：src/serial.cc + src/impl/unix.cc +
     src/impl/list_ports/list_ports_linux.cc（win/osx 分支文件不参与，与上游
     UNIX 分支选择一致）；
   - 标准 `install()` 到 lib/ 与 include/serial/（Conan CMAKE_INSTALL_PREFIX
     指向包目录），安装集与上游一致（serial.h + v8stdint.h + 库）；
   - 不编 serial_example 可执行文件 → 纯库包，按 R38 无需 commands.json；
   - 未引入任何平台宏（R8/PF5）：波特率/自定义波特率代码保留上游原有的
     `#ifdef Bxxxx`/`#elif defined(__linux__) && defined(TIOCSSERIAL)` 能力守卫。
2. **链接策略**：上游 Linux 分支 `target_link_libraries(serial rt pthread)`
   面向 glibc 拆分库；目标平台 libc 将 pthread/clock_gettime 收敛进 libc，
   补丁后无需额外链接（实测无未定义符号）。
3. **警告（不阻塞）**：上游 `#include <sys/signal.h>` 触发 sysroot 重定向
   warning（redirecting to signal.h），musl 行为，不改上游源码。
4. **构建系统**：cmake_minimum_required 提升至 3.10（Conan/CI 通用），项目
   声明 `VERSION 1.2.1 LANGUAGES CXX`。

## 4. 上游测试清点与实跑（R51）

清点（tarball 完整清单证据）：
- tests/unix_serial_tests.cc —— gtest，4 用例（readWorks/writeWorks/
  timeoutWorks/partialRead），openpty 主从回环，无需真实串口硬件；
- tests/unit/unix_timer_tests.cc —— gtest，2 用例（short_intervals/
  overlapping_long_intervals），MillisecondTimer 计时；
- tests/proof_of_concepts/mdc2250.cc —— 官方 1.2.1 包内为 11 字节残缺存根
  （内容仅 `#include ""`，不可编译；上游 GitHub 主分支同名文件才依赖 Roboteq
  控制器）→ 无法作为测试运行；
- tests/proof_of_concepts/tokenizer.cc —— 自含的 boost 字符串分词示例，
  与串口库无任何调用关系，非库测试；
- tests/proof_of_concepts/python_serial_test.py —— 需 pyserial 与真实串口
  硬件 → NOT_RUN（无硬件；且 CI 无 Python 测试面）；
- 上游断言数：serial 9 + timer 3 = 12（grep EXPECT_/ASSERT_ 计数）。

真机实跑（2026-09-19，clang++ 直接链接 build-lib/libserial.a，
gtest/1.17.0.2 + boost/1.91.0.1.3 头文件）：
- unix_serial_tests：**4/4 PASS**（单轮 510ms，稳定复跑通过）；
- unix_timer_tests：**2/2 PASS**（quiet 环境）；short_intervals 为 ±1ms
  计时敏感用例，共享设备忙时 2/7 轮出现 ±2ms 调度抖动失败
  （unix_timer_tests.cc:24，r+1 实测 -2 vs 容差 1），安静环境连续 4 轮全过，
  判定为调度抖动非功能缺陷，如实记录。

计数（单位：gtest case）：
- 上游清单 N = 6（4 + 2）；实际执行 N′ = 6；PASS = 6；FAIL = 0；
  SKIP = 0；NOT_RUN(非框架 poc，需硬件) = 3 项另计；
- 通过率：6/6（注：short_intervals 存在环境敏感 flakiness，7 轮实测
  5 过 2 挂，已注明）。

## 5. 消费者测试（test_package）

- test_package.cpp：链接打包产物后真实调用 serial::list_ports()（走
  list_ports_linux.cc 的 sysfs glob 路径）+ 5 组公共枚举值校验，
  6 项断言，退出码判定；计入鸿蒙特有消费者测试 1 项。

## 6. 其他

- 纯库包，无可执行产物 → 不声明 commands.json（R38）。
- 制品占用：libcxx-serial/1.2.1 在 ohpcd 制品仓无同名同版本记录（W0 实测），
  首次适配用上游版本号，无后缀。
