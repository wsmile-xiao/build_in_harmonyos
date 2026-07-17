# convmv — Converts filenames from one encoding to another

## 基本信息

| 项目 | 值 |
|------|-----|
| 名称 | convmv |
| 版本 | 2.06 |
| 许可证 | GPL-2.0 |
| 语言 | Perl |
| 构建系统 | makefile |
| 描述 | Converts filenames from one encoding to another |

## 编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 2.06 | built | 2026-05-21 |
| 2.06.1 | built | 2026-07-17 |

## 适配说明

- convmv 是纯 Perl 脚本，无 C 编译器依赖
- shebang 修改: `#!/usr/bin/perl` → `#!/usr/bin/env perl`（鸿蒙系统 `/usr/bin/perl` 不存在）
- 不支持 `--version` 选项，版本信息通过 `--help` 输出获取