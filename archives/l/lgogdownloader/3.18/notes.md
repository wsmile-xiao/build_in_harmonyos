# lgogdownloader 3.18 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15.0.4（target aarch64-linux-ohos, musl libc）
- profile: ci/conan/profiles/ohos-aarch64
- 状态: built

## 上游测试清点（R51）
- 源码树无 `tests/` 目录，`CMakeLists.txt` 无 `enable_testing()` / `add_test()`，
  无 ctest/pytest/meson 测试入口 → **上游自动化用例数 = 0**。
- 上游唯一自动化验证 = `.github/workflows/linux.yml`：release 构建后执行
  `cd build && ./lgogdownloader --help`（矩阵 g++/clang++ × QtGUI ON/OFF）。
- 该冒烟已集成进配方 `build()`：`can_run` 时执行 `--version` 与 `--help`。
- test_package 补全消费者验证 + 鸿蒙专项验证（不替代上游测试统计）。

## 编译步骤
```bash
conan create archives/l/lgogdownloader/3.18 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'json/json.h' file not found`；链接缺 `boost::iostreams` | 上游 `CMakeLists.txt` 用自带 `cmake/Find*.cmake`（pkg-config + `${Jsoncpp_INCLUDE_DIRS}` 等旧式变量）。Conan CMakeToolchain 设 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，改用 config 模式后旧式变量为空，include/libs 均未传播 | `patches/0001-CMakeLists.txt.patch`：改为链接 imported target（Boost::*/CURL::libcurl/JsonCpp::JsonCpp/tinyxml2::tinyxml2/rhash::rhash/Threads::Threads/ZLIB::ZLIB/Tidy::Tidy） |
| 2 | 链接报 `undefined symbol: boost::iostreams::detail::zlib_base::before` 等 | 制品仓 `boost/1.90.0.x`、`boost/1.91.0.x` 的配方显式 `BOOST_IOSTREAMS_ENABLE_ZLIB=False`，libboost_iostreams 未编入 zlib 过滤器 | 改用 `boost/1.85.0`（iostreams 含 zlib+gzip 后端，组件 `Boost::iostreams` 传递依赖 `zlib::zlib`） |
| 3 | `Version conflict: zlib/1.3.1 vs zlib/1.3.1.1` | boost/1.85.0 依赖 zlib/1.3.1，curl/8.15.0.1 依赖 zlib/1.3.1.1 | `self.requires("zlib/1.3.1.1", override=True)`（zlib ABI 稳定，统一到 curl 已用修订） |

## 源码修改
- `patches/0001-CMakeLists.txt.patch`：`target_include_directories` /
  `target_link_libraries` 由旧式变量 `FOO_INCLUDE_DIRS`/`FOO_LIBRARIES` 改为
  Conan imported target（含删除上游未定义、始终为空的 `${OAuth_*}` 变量）。
  未引入任何平台宏。

## 依赖版本
boost/1.85.0、curl/8.15.0.1、jsoncpp/1.9.8.1、tinyxml2/11.0.0、rhash/1.4.6、
tidy-html5/5.8.0、zlib/1.3.1.1（override）。

## 验证结果
```bash
# 编译 + 链接
conan create archives/l/lgogdownloader/3.18 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
# -> Build succeeded, lgogdownloader --version / --help 执行通过

# test_package（消费者冒烟 + 鸿蒙专项）
bash test_package/test_lgogdownloader.sh <bin> <work> <log>   # 3 组断言
bash test_package/ohos_specific_test.sh  <bin> <work> <log>   # AArch64 ELF / HarmonyOS 标识 / XDG 路径
```

## 注意事项
- 首次运行二进制会触发系统安全弹窗确认（鸿蒙平台行为）。
- `CMAKE_SYSTEM_PROCESSOR` 在 OHOS 上被 CMake 判为 `unknown`，故默认
  User-Agent 为 `LGOGDownloader/3.18 (HarmonyOS unknown)`；平台名 `HarmonyOS`
  正确（`CMAKE_SYSTEM_NAME`），仅架构字段为 unknown（上游行为，未做修改）。
---

**编译结束**: 2026-09-27 01:25
**最终状态**: built
