# simdjson 3.9.5 — 适配笔记

> 档案创建时间: 2026-09-01
> 当前状态: built (Conan 配方生成，待本地验证)

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | simdjson |
| 版本 | 3.9.5 |
| 构建系统 | CMake |
| 源码 URL | https://github.com/simdjson/simdjson/archive/refs/tags/v3.9.5.tar.gz |
| SHA256 | 3d9e894a0ded85c000ec5b6ed1450ab4b037f44ba95eb3b0fefb4cda72cd9dab |

> 版本头说明：官方 v3.9.5 tag 内 `include/simdjson/simdjson_version.h` 自动生成版本宏
> 为 `SIMDJSON_VERSION "3.9.4"`（simdjson release.py 生成，上游偶发未同步小版本）。
> 属官方源码固有内容，非本地修改；归档版本号按任务约定使用 3.9.5。

## 二、源码获取与网络

- 上游官方源 github.com 在本机（执行端）不可达（TCP 连接超时）。
- 经 ghfast.top 镜像通道获取同一官方 v3.9.5 tarball（SHA-256 与通道无关），
  conandata.yml 保留官方 github.com URL（R39：禁止 file:// 与本地缓存路径；
  CI 按 hint_rules github_timeout 自动注入镜像 fallback）。

## 三、依赖

无外部依赖。simdjson 自包含，仅依赖系统 pthread。

## 四、适配要点

1. 纯 C++ 库，CMake 构建；OHOS aarch64 工具链（clang 15.0.4）下可构建。
2. 参考同库已发布 4.6.3 配方；3.9.5 为独立新版本适配（ohpcd registry 无 3.9.5）。
3. 构建产物: libsimdjson.a (static, 默认) / libsimdjson.so (shared)。
4. 头文件: simdjson.h 单头文件（含 ondemand/DOM API）。
5. 需要链接 pthread (Linux/OHOS)。
