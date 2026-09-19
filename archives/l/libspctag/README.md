# libspctag

libspctag 是一个用 C 编写的轻量级库，用于读取和写入 SNES SPC 文件中的 ID666 元数据标签。

## 功能概述

- 识别并解析文本和二进制两种 ID666 标签格式；
- 读取歌曲名、游戏名、转储者、注释、日期、时长、淡出时长、艺术家、声道和模拟器字段；
- 修改标签字段并写回 SPC 文件；
- 同时支持 Conan 的共享库和静态库构建。

## OHOS 适配

- 使用 OHOS SDK Clang 和 CMake 原生构建，无第三方依赖；
- 显式使用 CMake 的 `OHOS` 平台模块，确保共享库具有正确的 SONAME；
- 对 CMake 4.x 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`，兼容上游的 CMake 2.6 策略声明；
- 修正上游头文件的全局符号定义和若干现代 Clang 暴露的未定义行为，使静态/共享消费方式均可用；
- 消费者测试覆盖文本与二进制 ID666 往返，另有 OHOS aarch64 专项临时目录读写测试。

## 依赖关系

- 编译依赖：CMake、C 编译器；
- 运行依赖：仅系统 C 库；
- 第三方 Conan 依赖：无。

## 参考资料

- 项目主页：<https://sourceforge.net/projects/libspctag/>
- 官方源码：<https://downloads.sourceforge.net/project/libspctag/libspctag-0.2.tar.gz>
- 文件格式说明：<https://snesmusic.org/files/spc_file_format.txt>
