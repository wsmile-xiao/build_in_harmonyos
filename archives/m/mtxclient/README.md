# mtxclient

Nheko 桌面客户端使用的 Matrix 客户端-服务器 API 库（C++20）。

- 上游：<https://github.com/Nheko-Reborn/mtxclient>
- 许可证：MIT
- 构建系统：CMake（仓库另有 meson.build，本适配不使用）

## 库内容

| 内容 | 说明 |
|------|------|
| `libmatrix_client.so.0.10.1` | 主库（SOVERSION 跟随项目版本） |
| `include/mtx/**` | 事件、请求、响应、标识符等数据结构 |
| `include/mtxclient/**` | HTTP 客户端、加密客户端、工具函数 |
| `lib/cmake/MatrixClient/**` | 导出目标 `MatrixClient::MatrixClient` |

## 主要依赖

`coeurl`（异步 HTTP，libcurl + libevent）、`olm`（Matrix 端到端加密）、`openssl`、
`nlohmann_json`、`re2`（推送规则正则）、`spdlog`。

## HarmonyOS PC 适配要点

1. **必须 C++20**：`include/mtx/identifiers.hpp` 使用 `std::strong_ordering` 与 `operator<=>`；
   `ci/conan/profiles/ohos-aarch64` 的 `compiler.cppstd=17` 需在配方中覆盖。
2. **OHOS 镜像没有 pkg-config**：系统与 hnp 树里既无 `pkg-config` 也无 `pkgconf`，
   而上游用 `pkg_check_modules` 探测 re2 / libevent_core / libevent_pthreads / libcurl / coeurl。
   配方以 `tool_requires("pkgconf/3.0.6")` 提供实现并固定 `PKG_CONFIG_EXECUTABLE`。
3. **两个可移植性补丁**（只改 `CMakeLists.txt`，不动源文件）：
   - `0001`：`Olm` → `olm`（libolm 3.2.x 与 ConanDeps 的包名/目标名都是小写）；
   - `0002`：gtest 测试目标改用当前名 `GTest::gtest` / `GTest::gtest_main`
     （gtest 1.14 删除了 `GTest::GTest`/`GTest::Main`）。
4. **已知运行期限制**：ohpcd 的 `libcurl/8.5.0` 为无 TLS 后端变体，
   真实 Matrix homeserver 的 HTTPS 通信会返回 `CURLE_UNSUPPORTED_PROTOCOL`。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.10.1 | built | 配方、补丁与 test_package 完成，本机门禁全通过；W0 依赖齐备，设备 conan create 待空闲窗口 |

详细分析与证据见各版本目录下的 `notes.md` 与 `reports/`。
