# libflac 1.5.0 适配笔记

## 编译环境

- 构建系统: CMake（xiph/flac 1.5.0，C99 + C++ for libFLAC++）
- 平台任务: contrib-13169（libflac 1.5.0），claimer Ember5843，认领 2026-09-15T16:05Z
- 目标平台: HarmonyOS PC arm64（clang 15 / musl），本机原生构建
- 依赖: **无外部依赖**（WITH_OGG=OFF；pthread/iconv 在 musl libc；链接 m）
- 上游: https://github.com/xiph/flac （xiph 官方 GitHub 镜像，2417 stars；tag 1.5.0）
- 源码 sha256: `aea54ed186ad07a34750399cb27fc216a2b62d0ffcd6dc2e3064a3518c3146f8`
- 语言实测（R47 lang-preflight）: 121 文件（c:95, cpp:25, bash:11, perl:1），主体 79% C/C++

## 源码面貌（摸底结论）

- 交付形态: `libFLAC.a`（static）/ `libFLAC++.a` + `flac`、`metaflac` 命令行 + 头文件
- 上游 CMake 选项: BUILD_CXXLIBS/PROGRAMS/EXAMPLES/TESTING/DOCS、WITH_OGG、
  WITH_FORTIFY_SOURCE、WITH_STACK_PROTECTOR、INSTALL_MANPAGES/PKGCONFIG/CMAKE_CONFIG
- WITH_OGG=OFF 分支完全不查 Ogg::ogg；ENABLE_MULTITHREADING 走 pthread
- 上游测试: CTest 注册 test_flac/test_metafile/test_grabbag/test_seeking/
  test_streams + test_libFLAC(++)——驱动 flac 二进制做真实编解码往返

## 移植要点

1. WITH_OGG=OFF + BUILD_PROGRAMS=ON + BUILD_TESTING=ON：ctest 真实执行上游套件
2. 构建环境显式清空 LD_LIBRARY_PATH（CI-021 ambient /usr/local/lib 的 libxml2
   会破坏 SDK lld——同 libodfgen/libabw 根因）
3. **上游 11 项 ctest 中 9 项执行通过，2 项平台差异排除**：test_libFLAC/test_libFLAC++ 的元数据迭代器用例依赖 Unix 权限位（chmod 444 后要求写入被拒）；hmdfs 不保留权限位（实测 chmod 444 后 append 成功），且设备上无用户可写的非 hmdfs 路径——前提不可能成立。以 ctest -E 排除并按 §8.6 归因为平台差异（hmdfs 无 Unix 权限位语义）；其余 9 项含 flac 命令行真实编解码往返、随机寻址全部通过，消费者无损往返测试另证
4. 组件化 package_info：flac / flac++ 两个组件，均带 cmake_target_name 与
   pkg_config_name；静态消费者补链 m

## 状态

- [x] 配方四件套
- [x] 设备实机 conan create + conan-verify + 上游 ctest + 消费者测试
- [x] push / PR / 平台绑定 / 提审
