# libee

> CEE-inspired 事件表达式库（结构化日志事件），Rainer Gerhards / Adiscon 出品，
> 早期 rsyslog / liblognorm 用于结构化内容表示的基础库。

## 基本信息

| 项目 | 信息 |
|------|------|
| 版本 | 0.4.1 |
| 许可证 | LGPL-2.1 |
| 来源 | http://www.libee.org |
| 构建系统 | autotools |
| 依赖 | libestr/0.1.11（运行时）；构建期 tool_requires automake/1.18 + libtool/2.5.4 |
| 补丁 | 无（autoreconf 重新生成 config.guess/sub，tool_requires automake 提供 OHOS 支持） |

## OpenHarmony 适配状态

- **编译状态**: 待真机预检回填
- **门禁验证**: 待真机预检回填
- **上游测试**: tests/ 下 genfile + ezapi1 两个 check 程序，配方实跑 `make check` 并用 fixture 执行 ezapi1 取证
- **补丁数量**: 0（tool_requires automake 自带 OHOS-aware config.guess/sub）

## 编译要点

- 官方 tar 包自带 2012 年生成的 configure，config.guess/config.sub 不识别 OHOS，需 `autoreconf -fiv` bootstrap
- configure.ac 用 `PKG_CHECK_MODULES` 查找 libestr，配方需 `requires libestr/0.1.11` + `PkgConfigDeps`
- OHOS 下显式传递 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`
- 构建产物含 `sbin/libee-convert`，按 R38 在软件级声明 commands.json
