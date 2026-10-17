# httpserver-h 0.0-git9029347a82 适配笔记

## 编译环境
- 构建系统: header-only（无编译阶段；上游 CMake 仅用于测试构建）
- 编译日期: 2026-09-27
- 编译器: clang/clang++ (15.0.4, aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

1. 下载官方 tarball（GitHub archive URL，codeload 可达；SHA-256 已核验并写入 conandata.yml）
2. 编写 header-only conanfile.py（变体 A：仅打包 httpserver.h + LICENSE）
3. test_package 编写真实消费者测试：`#define EPOLL` + `#define HTTPSERVER_IMPL` +
   include <httpserver.h>，启动 HTTP 服务器（epoll 后端），客户端 GET /hello，
   轮询驱动事件循环，验证 200 OK 与响应体
4. `conan create` 验证配方自包含性（G2）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 直连 github.com 超时 | 本机网络仅 api.github.com / codeload.github.com 可达 | 预置 codeload 官方 tarball 至 $TMPDIR/builds/ 并核验 SHA-256 后 init-build |
| 2 | ragel 缺失（上游测试构建需要） | 环境无 ragel | cmd-pkgs install.sh 安装 ragel 6.10（R18 预编译包优先） |
| 3 | 事件后端选择 | 头文件 impl 区 `#ifdef EPOLL ... #else <sys/event.h>` | 消费者须在 include 前定义 EPOLL（OHOS 支持 epoll_wait） |

## 源码修改

无（header-only 库，未修改上游源码）。
---

**编译结束**: 2026-09-27 22:22
**最终状态**: published
