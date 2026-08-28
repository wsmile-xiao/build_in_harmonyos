# restinio 0.6.19 — 适配记录

## 上游身份

| 项 | �值 |
|----|----|
| 库 | restinio |
| 版本 | 0.6.19 |
| 上游 | https://github.com/Stiffstream/restinio |
| tag | v.0.6.19 |
| 源码 URL | https://github.com/Stiffstream/restinio/archive/refs/tags/v.0.6.19.tar.gz |
| SHA256 | 5a739cac8f3148e7e94f05bb08f5cf569dd31f6f3ea2b893eddfffb0a155eb52 |
| 依赖源码 URL（Asio，独立第二来源） | https://github.com/chriskohlhoff/asio/archive/refs/tags/asio-1-28-1.tar.gz |
| 依赖源码 SHA256（Asio） | 5ff6111ec8cbe73a168d997c547f562713aa7bd004c5c02326f0e9d579a5f2ce |
| 许可证 | BSD-3-Clause |
| 构系统 | CMake (cmake_minimum_required 3.5) |
| 语言标准 | C++14 (SET(CMAKE_CXX_STANDARD 14), REQUIRED ON) |
| package_type | header-library (129 公共头在 dev/restinio/) |

## 依赖分类（required / optional / bundled / build-test）

| 依赖 | 分类 | Conan 来源 | 备注 |
|------|------|------------|------|
| fmt | required | ohpcd fmt/8.1.1 | restinio 公共 formatters facade 将格式化委托给 fmt::format |
| http-parser | required | ohpcd http-parser/2.9.4 | http_headers.hpp / websocket/ / impl/connection.hpp 直接 #include <http_parser.h> |
| asio | bundled | bundled snapshot 1.28.1 (Boost-1.0) | 上游 externals.rb 官方下载 chriskohlhoff/asio asio-1-28-1 到 dev/asio；ohpcd 无 asio 包 |
| asio_mxxru | build-test | — | 上游 externals.rb 仅 MxxRu 构建骨架用，Conan 配方不需要 |
| nodejs_http_parser_mxxru | build-test | — | 同上 |
| Catch2 | build-test | ohpcd catch2/* 可用 | 上游单测用 catch_main，本 header-only 配方不编译上游单测 |
| CMake | build | — | cmake_minimum_required 3.5 |

### Asio 实际模式与功能边界

restinio CMakeLists.txt 暴露 `RESTINIO_USE_BOOST_ASIO`（none/static/shared）。默认 none 即 standalone asio；上游 externals.rb 官方下载 chriskohlhoff/asio 1.28.1 到 dev/asio，作为 bundled 头文件使用（`#include <asio.hpp>`）。ohpcd 无 asio 包；boost/1.84.0 存在但 boost-asio 路线会引入整套 boost 依赖、对 header-only 包属过度。本配方选 bundled standalone-asio 路线（与上游 externals.rb 一致），cpp_info.defines 暴 ASIO_STANDALONE/ASIO_HAS_STD_CHRONO/ASIO_DISABLE_STD_STRING_VIEW。失去的功能边界：不使用 Boost.Asio 的 boost::system::error_code 軹名、boost::asio::ip 包装；standalone 路线完全覆盖 restinio 核心 HTTP server 用途。

### http-parser fallback 实际模式

restinio externals.rb 官方下载 nodejs/http-parser v2.9.4 到 dev/nodejs/http_parser/，restinio 用 `#include <http_parser.h>`。ohpcd http-parser/2.9.4 recipe 把 http_parser.h 安装到 package_folder/include、libhttp_parser.a 到 lib、cmake target `http_parser::http_parser`。本配方 Conan requires http-parser/2.9.4，消费者链接 http_parser::http_parser，不内置 http_parser 源码。

### fmt 实际模式

restinio formatters facade（restinio/formatters.hpp 等）将格式化委托给 fmt::format。ohpcd fmt/8.1.1 recipe cmake target `fmt::fmt`。本配方 Conan requires fmt/8.1.1，消费者链接 fmt::fmt。

## Conan 配方设计

- package_type = header-library；不编译任何二进制。
- 暴露 fmt/8.1.1 和 http-parser/2.9.4 作为 Conan requires（真实 ohpcd 平台包）。
- 打包 129 restinio 公共头到 include/restinio/，bundled standalone-asio snapshot 到 include/asio/。
- cpp_info.defines = [ASIO_STANDALONE, ASIO_HAS_STD_CHRONO, ASIO_DISABLE_STD_STRING_VIEW]（与上游 CMakeLists.txt 默认 standalone 趶线一致）。
- cmake target `restinio::restinio`，pkg-config `restinio`。

## test_package

消费者真实链接：find_package(restinio) + find_package(fmt) + find_package(http_parser)；target_link_libraries restinio::restinio fmt::fmt http_parser::http_parser；ASIO_STANDALONE 编译宏。断言 3 条：fmt �軹接、http_parser 笑号軹接、restinio request handler wired。OHOS 交叉构建用 qemu-aarch64 运行。

## sendfile 边界（见 E327 �草稿）

上游 samples/sendfile/main.cpp 在 OHOS 交叉构建下，CWD 不正导致相对路径假失败；正 CWD 下真实边界为 sendfile/main.cpp:644 Broken pipe 后 SIGSEGV，EXIT=139。本 header-only 配方不编译 sendfile 示例，该边界属上游示例在 OHOS 运行时边界，记录为知识草稿不弱化处理。
---

**编译结束**: 2026-08-27 15:22
**最终状态**: built
