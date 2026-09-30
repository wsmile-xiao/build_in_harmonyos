# WWWOFFLE — OpenHarmony 编译档案

## 软件简介
WWWOFFLE（World Wide Web Offline Explorer）是一个带缓存的 HTTP/FTP/finger 代理
服务器，专为拨号/离线浏览场景设计：在线时抓取页面并缓存，离线时直接从缓存读取。

## 功能概述
- HTTP、FTP、finger 协议缓存
- 支持 GET/HEAD/POST/PUT 等 HTTP 方法
- 命令行/交互式控制在线/离线/自动拨号状态
- 高度可配置（配置文件在 /etc/wwwoffle/）
- 缓存管理与多语言错误页

## 可执行文件
- `wwwoffle`      — 浏览器客户端（fetch/offline/autodial/config 等子命令）
- `wwwoffled`     — 代理服务守护进程
- `wwwoffle-tools`— 多调用工具（wwwoffle-ls/mv/rm/read/write/hash/fsck/gzip/gunzip）

## OHOS 适配要点
- 自带的 config.guess/config.sub 为 2010 版，无法识别 aarch64 与 HarmonyOS/OHOS；
  已替换为现代版本并加入 OHOS 检测（uname 报 OHOS 时产出 `aarch64-unknown-linux-ohos`）。
- 可选依赖 zlib/gnutls/gcrypt 通过 configure 关闭（`--with-*=no`）。
- 不强制静态链接（wwwoffle 为独立工具，非系统同名库；R26 仅针对系统同名库）。
- `make install` 会写系统目录并跑 fixup-install.sh，改用直接打包可执行文件。

## 依赖关系
- 无外部 conan 依赖（zlib/gnutls/gcrypt 可选，当前关闭）
- 构建期需要 flex/lex（configure 的 AC_PROG_LEX 硬性要求）

## 参考资料
- [官方下载页](http://www.gedanken.org.uk/software/wwwoffle/download/)
- [源码 SVN](https://gedanken.org.uk/svn/wwwoffle/trunk/)

## conan
- 版本：2.9j（首次适配）
- 配方路径：`archives/w/wwwoffle/2.9j/`
- 上游测试：`src/testprogs/` 5 个诊断测试程序（无 make check，逐个运行）
