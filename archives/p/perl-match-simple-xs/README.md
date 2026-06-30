# perl-match-simple-xs

Perl XS 实现的简单模式匹配模块。

## 描述

match-simple-XS 是 match-simple 模块的 XS（C 扩展）实现，提供高性能的模式匹配功能。

## 版本历史

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 0.002 | built | 2026-06-15 |

## 功能

- Perl XS 扩展模块
- 提供高性能模式匹配
- 作为 match-simple 的加速实现

## 依赖

- perl (>= 5.42.0)
- match-simple (纯 Perl 实现)

## 使用方法

```perl
use match::simple::XS;
# 与 match-simple 功能相同，性能更高
```

## 安装

用户通过 cmd-pkgs 公共安装脚本安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-match-simple-xs 0.002
```

## 注意事项

由于 OpenHarmony SELinux HMDFS 限制，XS 模块需要安装到系统目录才能正常加载。