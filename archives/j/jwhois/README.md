# jwhois

**GNU 改进版 whois 客户端**（查询 WHOIS 服务器并跟随 referral 转介链）

jwhois 是 GNU 项目维护的 whois 命令行客户端，根据配置决定查询服务器、支持 referral 转介链跟踪、rwhois 扩展查询与 HTTP 代理查询。

## 用法

```bash
jwhois [OPTIONS] [QUERY]
```

| 选项 | 说明 |
|------|------|
| `-c, --config=FILE` | 使用指定配置文件（默认 `SYSCONFDIR/jwhois.conf`） |
| `-h, --host=HOST` | 强制指定查询主机 |
| `-p, --port=PORT` | 强制指定查询端口（默认 43） |
| `-f, --force-lookup` | 强制查询（即使有缓存） |
| `-d, --disable-cache` | 禁用缓存 |
| `-v, --verbose` | 详细输出 |
| `--version` | 输出版本信息 |
| `--help` | 输出帮助信息 |

## 鸿蒙适配

- 构建系统：Autotools（release tarball 自带 configure）
- 关键配置：`--disable-nls`（OHOS musl 无 libintl）；`--build=aarch64-unknown-linux-gnu`（2007 年版 config.guess 不识别 OHOS）
- 补丁：VPATH 构建 gnulib 链接路径修正（`top_srcdir` → `top_builddir`）
- 产物：`bin/jwhois`、`etc/jwhois.conf`
