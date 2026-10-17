# libpreludedb

> Prelude SIEM 的 IDMEF 数据库抽象层（SQL 后端以 dlopen 插件加载，选择/判据与后端无关）。

## 简介

libpreludedb 建立在 [libprelude](../libprelude/) 之上：把 IDMEF 告警与心跳落库并查询，
向上提供与数据库无关的路径选择（selection）与判据（criteria）处理、classic 格式插件、
告警插入/查询 API；向下以 dlopen 插件方式接 MySQL / PostgreSQL / SQLite3。Prelude 各
组件（`prewikka`、`prelude-correlator`、`prelude-lml` 等）都通过它访问告警库。

本次适配对象为 5.2.0（上游最后一个 5.x 正式版，2020-09-09 发布），autotools 构建，
唯一强制依赖为同版本的 libprelude。

## 上游地址说明

原官网域名（`prelude-labs.org` / `www.prelude-siem.org`）已被劫持失效，官方发布页的
`libpreludedb-5.2.0.tar.gz` 均为 404，无法校验也无法作为可信源。本目录的配方改用
**Prelude-SIEM 官方 GitHub 组织的 tag 归档** 作为上游源：

```
https://github.com/Prelude-SIEM/libpreludedb/archive/refs/tags/5.2.0.tar.gz
sha256: fdbfb75f3ae02e016f05881dabb6c2d588b1ae9896624cb46594e765f8b4b261
```

该归档没有 autoreconf 产物（`configure`/`Makefile.in`/`config.h.in` 未提交），因此
配方在 `build()` 内自举，等价上游 `autogen.sh`。

## OHOS 适配要点

- **依赖桥接**：上游 `AM_PATH_LIBPRELUDE(5.2.0, ...)` 只认 `libprelude-config` 脚本并
  `AC_TRY_RUN` 运行探测程序，而 ohpcd 的 libprelude 制品按 R38 只交付库 → 配方在
  `generate()` 里生成最小兼容层，并用 `append_path` 注入 `PATH`/`LD_LIBRARY_PATH`。
- **traits**：公开头文件 `#include <libprelude/...>`，因此 libprelude 必须声明
  `transitive_headers=True, transitive_libs=True`（否则消费端拿不到传递依赖的头文件）。
- **平台兼容**：自举 + config.guess 注入 HarmonyOS 分支（E007）、放宽 `configure` 的
  `umask 077`（E011）、in-tree 布局规避生成头路径问题；**无源码补丁**。
- **测试**：上游测试入口为随树发布的 vendored gnulib 自检 `libmissing/tests`，实跑
  44/44 通过（0 skip / 0 fail）；另有配方自带 test_package 消费者测试。
- **交付面**：库 + 头文件 + classic 格式插件 + `libpreludedb.m4`；`preludedb-admin`
  等运维脚本、语言绑定（需 swig）、gtk-doc 文档均剔除或显式关闭。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| [5.2.0](5.2.0/) | built | 首次适配（OHOS aarch64，clang 15） |