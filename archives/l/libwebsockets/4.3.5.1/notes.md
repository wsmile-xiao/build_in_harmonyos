# libwebsockets 4.3.5.1 适配笔记

## 版本身份

- 平台版本: 4.3.5.1（R37 适配修复后缀，**不是**新上游版本）
- 上游源码版本: v4.3.5
- 官方仓库: https://github.com/warmcat/libwebsockets
- 源码 URL: https://github.com/warmcat/libwebsockets/archive/refs/tags/v4.3.5.tar.gz
- SHA256: 87f99ad32803ed325fceac5327aae1f5c1b417d54ee61ad36cffc8df5f5ab276
- 许可证: MIT（部分源码 BSD / CC0）

## 任务背景

- 任务类别: 依赖项修复（Issue #2222）
- 历史任务: libwebsockets 4.3.5（Issue #2171，PR #5344，已发布 libwebsockets/4.3.5）
- 下游任务: ttyd 1.7.7（Issue #2148，分支 feat/ttyd-1.7.7-WMY1）
- 根因: ttyd 1.7.7 的 CMakeLists.txt 无条件要求 libwebsockets 启用 libuv
  支持（`check_symbol_exists(LWS_WITH_LIBUV "lws_config.h" ...)`，未定义即
  `FATAL_ERROR "libwebsockets was not build with libuv support"`），
  而 4.3.5 包内 lws_config.h 为 `/* #undef LWS_WITH_LIBUV */` 且配方未声明
  libuv 依赖、未设置 LWS_WITH_LIBUV=ON。

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-08-16
- 编译器: clang / clang++（Conan OHOS profile，ohos-aarch64）
- 状态: built（conan-verify 通过，未提交 release/upload CI，故不标记 published）
- 平台: OpenHarmony PC (aarch64)

## 编译步骤

```bash
# Conan 配方验证（含干净构建 + test_package 消费者测试）
conan create archives/l/libwebsockets/4.3.5.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -r=ohpcd --build=libwebsockets/4.3.5.1 -c tools.build:jobs=1
```

关键 CMake 选项：

- `LWS_WITH_LIBUV=ON`：启用 libuv 事件循环集成（本轮核心修复）
- `LWS_WITH_EVLIB_PLUGINS=OFF`：libuv 直接编入 libwebsockets，而非运行时插件
- `LWS_LIBUV_INCLUDE_DIRS` / `LWS_LIBUV_LIBRARIES`：显式指向 Conan libuv/1.52.1 包
- `LWS_WITH_SSL=ON`：启用 OpenSSL（依赖 openssl/3.5.6，沿用 4.3.5）
- `LWS_WITH_HTTP2=ON`、`LWS_WITH_CLIENT=ON`、`LWS_WITH_SERVER=ON`
- `LWS_WITHOUT_TESTAPPS=ON`、`LWS_WITH_MINIMAL_EXAMPLES=OFF`：包内不构建演示/测试程序
- `LWS_WITH_NETLINK=ON`、`LWS_WITH_IPV6=ON`
- `CMAKE_POLICY_VERSION_MINIMUM=3.5`：规避 CMake 策略版本问题

## 依赖变化（相对 4.3.5）

| 依赖 | 版本 | 变化 | 说明 |
|------|------|------|------|
| openssl | 3.5.6 | 不变 | LWS_WITH_SSL 必需；制品仓已发布 |
| libuv | 1.52.1 | **新增** | LWS_WITH_LIBUV 必需；制品仓已发布 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ttyd 1.7.7 configure 失败：libwebsockets was not build with libuv support | 4.3.5 配方未启用 LWS_WITH_LIBUV、无 libuv 依赖 | 新增 libuv/1.52.1 依赖 + LWS_WITH_LIBUV=ON |
| 2 | 外部 libuv 定位 | 上游 CMake 对 LWS_LIBUV_INCLUDE_DIRS/LWS_LIBUV_LIBRARIES 为空时回退 find_path/find_library，交叉编译下可能误中宿主系统库 | generate() 显式从 libuv Conan 包路径传入这两个变量 |
| 3 | 运行时插件加载复杂化 | LWS_WITH_EVLIB_PLUGINS 默认 UNIX 下为 ON | 设 OFF，libuv 直接编入 libwebsockets |
| 4 | OHOS 头文件冲突 | 同 4.3.5（linux/if_addr.h、linux/netlink.h 与 musl sys/socket.h 的 sockaddr_storage 冲突） | 沿用 4.3.5 的 0001/0002 补丁 |

## 源码修改

- 沿用 4.3.5 的两个 OHOS 平台头文件兼容补丁：
  - `patches/0001-lib-core-net-client-sort-dns.c.patch`：portability
  - `patches/0002-lib-roles-netlink-ops-netlink.c.patch`：portability
- 本轮 R37 修复新增一个符号导出补丁：
  - `patches/0003-lib-event-libs-libuv-libuv.c.patch`：portability。
    在 `-fvisibility=hidden` 下，libuv.c 中公开 libuv 集成 API
    （lws_uv_getloop、lws_libuv_static_refcount_add/del）的定义未继承
    LWS_VISIBLE（lws-service.h 声明块被 UV_ERRNO_MAP 条件跳过），
    导致符号未从 libwebsockets.so 导出、消费者无法链接；
    本补丁为这三个函数定义显式加 LWS_VISIBLE。

## 验证结果

```bash
# conan create（含 test_package 消费者测试）
# 退出码 0；test_package lws_consumer 运行通过全部断言（详见 test_package/MANIFEST.yml）
# 包内 lws_config.h 已为 #define LWS_WITH_LIBUV
```

上游测试说明：libwebsockets 4.3.5 上游无随包 CTest 自动测试（test-apps 为演示程序，
api-tests 需单独以 `LWS_WITH_MINIMAL_EXAMPLES=ON` 构建且部分依赖网络）。本版本在
package 构建时关闭 minimal examples，消费者验证由 test_package 的真实程序执行
（见 test_package/MANIFEST.yml 与最终报告中的上游测试统计）。

## 下游兼容性

- ttyd 1.7.7 的 `check_symbol_exists(LWS_WITH_LIBUV "lws_config.h" ...)` 在本包
  lws_config.h 上应返回真，CMakeLists.txt:64 的 FATAL_ERROR 消失。
- 临时 ttyd configure 验证仅作下游兼容证据，不混入 libwebsockets 上游测试统计，
  临时源码与构建产物不进入本 PR。

## 注意事项

- 本库是 ttyd 1.7.7（主任务 Issue #2148）的前置依赖，消费者可通过 Conan 直接
  `self.requires("libwebsockets/4.3.5.1")` 使用。
- 不得将本归档标记为 published，除非 release/upload CI 已真实发布到制品仓。
---

**编译结束**: 2026-08-16 14:42
**最终状态**: built
