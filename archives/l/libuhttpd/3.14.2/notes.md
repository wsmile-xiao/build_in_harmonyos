# libuhttpd 3.14.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 (OHOS aarch64, conan profile ci/conan/profiles/ohos-aarch64)
- 状态: published

## 编译步骤

1. 上游源码: `https://codeload.github.com/zhaojh329/libuhttpd/tar.gz/refs/tags/v3.14.2`（sha256 729e2f5d…）
2. **子模块补齐**：GitHub source archive 不含 submodule 内容（src/buffer、src/http-parser、src/log、src/ssl 均为空目录）。按 v3.14.2 tag 树（api.github.com tree 核验）锁定的 commit 分别从 codeload 拉取并布局：
   - src/buffer ← zhaojh329/buffer @ 1237374586
   - src/http-parser ← nodejs/http-parser @ a0c034c0（含上游测试 test.c）
   - src/log ← zhaojh329/log @ 1aa7ee85
   - src/ssl ← zhaojh329/ssl @ 65eb4601
   conandata.yml 中声明为 submodules，source() 逐个 get（显式 filename 以识别 tar.gz 格式）
3. CMake configure：`cmake -S . -B build -DCMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 4.1.2 移除 <3.5 兼容）+ libev/openssl 依赖目录注入
4. `cmake --build` → libuhttpd.so + 3 个示例
5. `conan create`（OHOS profile）→ 配方自包含构建通过，test_package 功能测试通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure: "Compatibility with CMake < 3.5 has been removed" | 上游声明 `cmake_minimum_required(VERSION 3.0)`，设备 CMake 4.1.2 移除旧版兼容 | toolchain 变量 CMAKE_POLICY_VERSION_MINIMUM 设置太晚（min 版本在加载 toolchain 前解析），改用 replace_in_file 提升源码声明为 3.5（adlplug/1.0.2 先例） |
| 2 | src/ssl 为空目录导致 add_subdirectory 失败 | GitHub source archive 不含 submodule 内容 | conandata.yml submodules 按 tag 锁定 commit 分别拉取（ableton-link/adlplug 先例） |
| 3 | conan get(): BadZipFile | codeload URL 以 commit SHA 结尾（无 .tar.gz 后缀），conan 无法识别压缩格式 | get() 显式传 filename="<name>.tar.gz" |
| 4 | 编译缺 openssl/ssl.h | 上游 ssl 子模块用 pkg_check_modules 找 OpenSSL 但读取**单数** `OPENSSL_INCLUDE_DIR`（pkg-config 只设复数 OPENSSL_INCLUDE_DIRS） | generate() 从 conan openssl 依赖显式注入 `OPENSSL_INCLUDE_DIR` 与 `OPENSSL_LIBRARIES` |
| 5 | 上游 make check / ctest 无测试（0 项） | libuhttpd 主库 CMake 未注册测试 | R51 清点：vendored http-parser 子模块自带 nodejs/http-parser 测试套件（v2.9.3），实际编译运行通过（exit 0）；test_package 写真实 HTTP 回环功能测试 |
| 6 | test_package 测试卡死 | 单线程事件循环：客户端阻塞在 recv 时事件循环无法 accept；chunked 响应 + Connection: close 下 recv 等 EOF 无界 | 客户端请求移至独立线程（libev 允许跨线程 ev_break）+ connect 重试 + SO_RCVTIMEO 5s 兜底 + 20s watchdog |

## 依赖版本
- libev/4.33（制品仓已发布，W0 通过）
- openssl/3.5.6（制品仓已发布）

## 验证结果
- conan create（OHOS aarch64 profile）：通过，Package created
- test_package 功能测试：HTTP/1.1 200 OK，响应体 "Hello from libuhttpd 3.14.2" 校验通过
- vendored http-parser 上游测试套件：全量通过（responses okay / requests okay, exit 0）

## 交付物
- conanfile.py（CMake 型配方，libev/openssl 依赖，子模块补齐）
- conandata.yml（主源码 + 4 子模块 + sha256）
- test_package/（真实 HTTP 回环功能测试 + MANIFEST.yml 上游测试声明）
---

**编译结束**: 2026-09-27 19:19
**最终状态**: published
