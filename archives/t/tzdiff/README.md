# tzdiff

**Display timezone differences with localtime in CLI**

## 简介

tzdiff 以当前（或 `-t` 指定的）时间为起点，逐小时并排列出多个时区的时间，
最后一列为本地时间，方便跨时区约会议时间。上游为单个 POSIX sh 脚本。

## 编译状态

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 1.2.1 | built | none (sh) | 2026-09-25 |

## 安装

```bash
# 从预编译包安装（注：该命令在制品仓发布（status=published）后生效）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- tzdiff 1.2.1

tzdiff -v
```

## 使用示例

```bash
# 东京、纽约与本地时间，从 2024-07-01 09:00 UTC 起列 3 小时
tzdiff -n 3 -t 2024-07-01T09:00Z Asia/Tokyo America/New_York

# 短名匹配
tzdiff Tokyo London
```

## 注意

- 鸿蒙 PC 没有 `/usr/share/zoneinfo` 目录树；包内自带 IANA zoneinfo（tzdata 2026.3），
  `TZDIR` 未设置时自动使用。可 `export TZDIR=<olson 目录>` 改用其他数据。
