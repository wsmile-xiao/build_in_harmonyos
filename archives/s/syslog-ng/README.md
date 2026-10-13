# syslog-ng

> 增强型日志守护进程：高可靠日志收集、过滤、解析与转发（syslog/JSON/网络多来源），模块化 dlopen 架构

## 简介

syslog-ng 是经典的系统日志基础设施，在 syslog 协议之上提供灵活的过滤、解析（正则、JSON、kv 等）与多目标路由（文件、网络、数据库等）。4.x 采用模块化设计：核心框架 `libsyslog-ng.so` + 运行时 dlopen 的模块（`lib/syslog-ng/*.so`），模块目录可在运行期经 `SYSLOGNG_PREFIX` 重定位。

本归档为 OpenHarmony PC（aarch64，OHOS 6.0，clang15/libc++）适配版，Conan 2 配方构建，`package_type=application`。构建期开启上游单元测试（criterion 驱动）；`make check` 在设备构建树内全量实跑（构建后另行执行，见 `4.8.1/notes.md`）。

## OHOS 适配要点

- **config.guess/config.sub 各两份**：顶层与捆绑的 `lib/ivykis` 都需要 HarmonyOS triplet 识别补丁（ivykis 经 `AC_CONFIG_SUBDIRS` 再跑一次 configure）。
- **E011 umask**：两处 configure 的 `umask 077 && mktemp -d` 在 HMDFS 上不可写，统一改为 022。
- **pkg 变量短路**：GLIB/PCRE2/OPENSSL/JSON/CRITERION 五组致命检查经 `<VAR>_CFLAGS/<VAR>_LIBS` 环境变量直接注入包内真实路径（制品仓 .pc 为 relocatable 打包，前缀是 `/`，不可直接用）。JSON 的模块名探测（`PKG_CHECK_EXISTS`）不吃变量短路，用 `PKG_CONFIG_PATH` 保证可发现。
- **模块目录重定位**：编译期默认 `${exec_prefix}/lib/syslog-ng`；运行期以 `SYSLOGNG_PREFIX` 指向包前缀即可 dlopen 模块（`lib/reloc.c` `lookup_sysprefix`）。
- **测试**：`criterion/2.4.3` 走 `test_requires`；configure 探测到 criterion≥2.2.1 即自动开启单元测试（无显式开关），测试程序在设备缓存构建树内 `make check -j1` 全量编译并运行。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.84.0.1 | 必须 shared 单实例（dlopen 模块共享 gobject 类型系统） |
| pcre2 | 10.45 | 正则过滤/解析（libpcre2-8） |
| openssl | 3.5.6 | TLS/加密（含 tls 模块） |
| json-c | 0.18 | JSON 解析模块（头以 `<json.h>` 包含，需 include/json-c 子目录） |
| libcurl | 8.5.0 | http 模块（`--with-libcurl`） |
| criterion | 2.4.3 | 上游单元测试框架（test_requires，仅构建期） |

## 功能验证

```bash
# 环境由 conanrun 提供（PATH/LD_LIBRARY_PATH/SYSLOGNG_PREFIX）
syslog-ng --version                 # 横幅 + Module-Directory 应指向包前缀 lib/syslog-ng
syslog-ng --module-registry         # 全量 dlopen 模块（无 Status: Unable）
syslog-ng -s -f test.conf           # 配置解析
syslog-ng --check-startup --no-caps -f test.conf   # 完整启动检查
```

端到端消费者测试（`test_package/test.sh`，14 项检查）覆盖：版本横幅/模块目录重定位/模块注册表/配置解析/启动检查/守护进程 internal()→file() 路由 + `syslog-ng-ctl stats` + SIGTERM 优雅退出。

## 参考

- [官方文档](https://www.syslog-ng.com/technical-documents/)
- [源码仓库](https://github.com/syslog-ng/syslog-ng)
