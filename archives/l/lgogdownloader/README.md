# LGOGDownloader 3.18 — HarmonyOS PC 适配记录

## 概述

LGOGDownloader 是 GOG.com 的非官方开源下载器，使用 GOG Galaxy API（Linux 版官方客户端缺失时的替代方案）。命令行工具，提供登录、游戏列表、下载、校验/修复、Galaxy 构建安装等功能。

- 上游仓库：https://github.com/Sude-/lgogdownloader
- 许可证：WTFPL
- 构建系统：CMake（>= 3.18）

| 项目 | 值 |
|------|-----|
| 目标平台 | HarmonyOS PC / OpenHarmony (aarch64) |
| 编译器 | clang 15.0.4 |
| C 库 | musl libc |
| 三元组 | aarch64-linux-ohos |
| 编译状态 | ✅ 通过（conan create + test_package 全绿） |

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| boost | 1.85.0 | filesystem / regex / program_options / date_time / iostreams（zlib+gzip 过滤器） |
| curl | 8.15.0.1 | HTTP(S) 下载 |
| jsoncpp | 1.9.8.1 | JSON 解析（API 响应） |
| tinyxml2 | 11.0.0 | XML 解析 |
| rhash | 1.4.6 | 文件哈希校验（CRC32/MD5 等） |
| tidy-html5 | 5.8.0 | HTML→XHTML 转换 |
| zlib | 1.3.1.1 | Boost.Iostreams 压缩后端 |

## 适配要点

1. **构建系统依赖发现方式改造**（`patches/0001-CMakeLists.txt.patch`）
   上游 `CMakeLists.txt` 用自带的 `cmake/Find*.cmake`（pkg-config + 旧式
   `FOO_INCLUDE_DIRS`/`FOO_LIBRARIES` 变量）发现依赖。鸿蒙构建的依赖来自
   Conan 制品仓，其 CMakeDeps 只导出 imported target，旧式变量为空，
   导致 `json/json.h` 找不到、链接缺 `boost::iostreams` 等。补丁改为直接
   链接 imported target。

2. **Boost 版本选择（关键）**
   `boost::iostreams::filter::zlib` / `gzip` 需要 libboost_iostreams 编译时
   带 zlib 后端。制品仓中 `boost/1.90.0.x`、`boost/1.91.0.x` 均显式设置
   `BOOST_IOSTREAMS_ENABLE_ZLIB=False`，链接期报
   `undefined symbol: boost::iostreams::detail::zlib_base::before`。
   `boost/1.85.0` 为手动编译且 iostreams 含 zlib 后端（组件 `Boost::iostreams`
   传递依赖 `zlib::zlib`），故选用之。

3. **zlib 版本冲突**
   `boost/1.85.0` 基于 `zlib/1.3.1`，`curl/8.15.0.1` 基于 `zlib/1.3.1.1`，
   图冲突。zlib ABI 稳定，用 `self.requires("zlib/1.3.1.1", override=True)`
   统一到 curl 已用的较新修订。

4. **Qt GUI 关闭**
   `-DUSE_QT_GUI=OFF`（上游默认），避免引入 Qt WebEngine。

## 验证

- `conan create`（ohos-aarch64 profile）编译 + 链接通过
- test_package：消费者冒烟 + 鸿蒙专项测试全绿
- 上游仅 `--help` 冒烟（无自动化测试套件），已在 build() 中执行
