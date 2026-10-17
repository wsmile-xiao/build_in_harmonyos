# Bareos Client

> Bareos 开源备份套件的可移植文件守护进程客户端（bareos-fd）。

## 简介

Bareos（Backup Archiving Recovery Open Sourced）是一套跨网络的开源备份
解决方案，源自 Bacula 项目。本配方构建上游官方定义的 universal client
配置：文件守护进程 `bareos-fd` 及其支撑库，不含 Director、Storage Daemon、
bconsole 与 WebUI。

`bareos-fd` 运行在被备份的机器上，接受 Director 的指令执行备份与恢复
任务，是备份体系中的客户端组件。

## OHOS 适配要点

- 使用 `-DBUILD_UNIVERSAL_CLIENT=ON`（上游可移植预设），自动进入
  client-only 模式并关闭 python/gfapi/jansson/lzo/capability/bconsole。
- 上游 CMake 在 configure 期经 CPM 从 GitHub 拉取 6 个依赖
  （CLI11/fmt/GSL/expected/utfcpp/xxHash）；OHOS 构建环境 configure 期
  不宜访问外网，配方把六包源码写入 conandata `deps` 并以
  `CPM_<NAME>_SOURCE` 注入本地解压目录。
- 上游单元测试目录 `core/src/tests` 在找不到 GTest 时被静默跳过；
  配方在 build() 内先构建安装自带的 googletest 1.14.0，再以
  `GTest_ROOT` 传给主 configure，保证 ctest 真实运行。
- OHOS 无 `sys/acl.h`（默认 `-Dacl=ON` 会 configure FATAL），改传
  `-Dacl=OFF`；xattr 缺失由上游 `HAVE_XATTR` 守卫自动降级，无需补丁。
- 内部库全静态（`-DBUILD_SHARED_LIBS=OFF`），交付物仅为
  `bin/bareos-fd`，不污染系统库目录。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| openssl | 3.5.6 | TLS/加解密（制品仓已发布） |
| zlib | 1.3.1 | 压缩/解压（制品仓已发布） |

构建期自带（不进交付物）：CPM 六包源码、googletest 1.14.0 源码。

## 功能验证

```bash
bareos-fd --version
```

完整备份功能需对接远端 Bareos Director（OHOS 本机无 Director，
测试止于二进制可执行验证）。

## 参考

- [官方文档](https://docs.bareos.org/)
- [源码仓库](https://github.com/bareos/bareos)
- [25.0.4 发布说明](https://github.com/bareos/bareos/releases/tag/Release%2F25.0.4)
