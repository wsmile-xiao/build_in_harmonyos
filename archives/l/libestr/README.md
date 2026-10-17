# libestr

> Some essentials for string handling (and a bit more)

libestr 是一个轻量级 C 字符串处理库，主要作为 rsyslog 日志系统的依赖库使用。

## 基本信息

| 项目 | 信息 |
|------|------|
| 版本 | 0.1.11 |
| 许可证 | LGPL-2.1 |
| 来源 | https://github.com/rsyslog/libestr |
| 构建系统 | autotools |
| 依赖 | 无运行时依赖；构建期 tool_requires automake/1.18 + libtool/2.5.4 |
| 补丁 | 无（autoreconf 重新生成 config.guess/sub，tool_requires automake 提供 OHOS 支持） |

## OpenHarmony 适配状态

- **编译状态**: ✅ published
- **门禁验证**: ✅ PASS (G1-G4)
- **功能测试**: ✅ 29/30
- **补丁数量**: 0（tool_requires automake 自带 OHOS-aware config.guess/sub）

## 编译要点

- GitHub tarball 不含 configure，需 `autoreconf -fiv` bootstrap
- 系统 automake 自动安装 OHOS-aware 的 config.guess/config.sub
- `install-sh~` 触发 automake BUG.am 警告，需删除

## 已知上游缺陷

⚠️ **es_str2num 十六进制 bug**: `es_str2num("0xFF")` 返回 85（应为 255）。上游代码缺陷。