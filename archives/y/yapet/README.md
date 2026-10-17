# yapet

`yapet`（Yet Another Password Encryption Tool）是一个 curses 界面的密码管理工具：
它把密码记录加密保存在单个 `.pet` 文件中（Blowfish / AES-256，经 OpenSSL EVP 实现，
密钥派生使用 Argon2），并提供命令行转换器在加密容器与 CSV 之间互转。

## 功能概述

- `yapet` — 终端（curses）密码管理器主程序，管理单文件加密密码库
- `csv2yapet` / `yapet2csv` — 加密 `.pet` 容器与 CSV 的双向转换器
- `libyacurs` — 上游捆绑的 curses 组件库（widget 层；**仅参与构建并静态链进三个 CLI，不安装**——顶层 `configure` 无条件向子配置注入 `--disable-install`，故按 `noinst_LTLIBRARIES`/`noinst_HEADERS` 构建）
- 支持 Blowfish、AES-256 两种加密算法与 Argon2 密钥派生；自 2.6 起支持 OpenSSL 3.0

## OHOS 适配

- **构建系统**: autotools（发布版 tarball 自带 `configure`，无需 autoreconf 自举）
- **依赖**: `openssl`、`argon2`、`ncurses`（硬依赖，configure 阶段 PKG_CHECK/AX_CHECK 探测）、
  `cppunit`（`make check` 用例）、`gettext`（tool_requires，提供 `msgfmt`）
- **平台适配**:
  - tarball 自带 `config.guess`/`config.sub`（2018-08-29，顶层与 `libyacurs/build-aux/` 各一份）无法识别
    `uname -s=HarmonyOS` → 整文件补丁升级到 2026-05-17 并注入 HarmonyOS 分支（E007 族）；
    不传 `--build`/`--host`（R1）
  - `PKG_CHECK_MODULES([ARGON2], [libargon2])` 模块名与 conan 包默认 `.pc` 名不一致 →
    配方内 `PkgConfigDeps.set_property()` 消费者侧改名
  - 上游 `tests/converters/check-local` 硬编码 `/tmp` 夹具路径（OHOS `/tmp` 只读）→
    补丁迁入构建目录；`tests/preload` 的 `istty` 门控块在无 tty 环境按上游自身逻辑整块跳过（计 SKIP）
- **产物**: `bin/{yapet,csv2yapet,yapet2csv}`、man/HTML 文档（实测 `make install` 仅落 `bin/` 与 `share/`；捆绑 `libyacurs` 被顶层 configure 强制 `--disable-install`，**不产 `lib/` 与 `include/`**）
- **上游测试**: `make check`（tests/ 8 个子目录 cppunit 套件 + converters/preload 的 check-local + 捆绑 libyacurs 测试）

## 依赖关系

- 编译依赖: openssl、argon2、ncurses、cppunit（pkg-config 模块探测）
- 工具依赖: gettext（msgfmt）
- 运行依赖: openssl、argon2、ncurses（静态链接进产物，随 conan 包分发）

## 参考资料

- 官网: https://yapet.guengel.ch/
- 源码: https://yapet.guengel.ch/downloads/
- 问题追踪: https://github.com/RafaelOstertag/yapet/issues

## Versions

| Version | Status | 说明 |
|---------|--------|------|
| 2.6 | built | 首个 OHOS 适配版本（任务卡 12260） |
