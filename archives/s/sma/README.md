# sma

SMA - Sendmail log analyser：把 sendmail 写的 syslog 文件读成流量报告
（ASCII / HTML / clog 三种格式），输出 envelope 收发件人排行、relay 排行、
按小时的投递分布、错误（SYSERR / mail loop / too many hops / ruleset rejection）
与队列统计（Sent / Deferred / Queued）。

- 上游：Jarkko Turkulainen，`http://www.klake.org/sma/`（发布页
  `http://www.klake.org/sma/download.html` 仍在线，但已不再对外提供 tarball，
  详见 `1.4/notes.md` 的取源定案表）
- 许可证：BSD-2-Clause（`COPYRIGHT`，2000-2003 Jarkko Turkulainen）
- 语言/构建：纯 C + 裸 Makefile（无 configure / CMake / Meson）
- 链接期依赖：**零**（Makefile 里没有任何 `-l` 标志，只用 libc；
  BSD 正则仅在 `_WIN32` 下走 `regex/` 里的自带源码，非 Windows 走系统 `<regex.h>`）

## 已适配版本

| 版本 | 目录 | 状态 |
|------|------|------|
| 1.4 | `1.4/` | built（本地真机验证，见 `1.4/notes.md`） |

## 用法速记

```
sma [OPTIONS] [files...]
  -h            打印用法（含版本号）后退出
  -a / -w / -O  ascii / html / 指定格式（ascii|html|clog）
  -o <file>     报告写入 <file>（缺省写 stdout）
  -C <string>   报告抬头（默认 conf.h 的 COMMENT）
  -f <file>     指定配置文件（默认 ./sma.conf，相对当前目录）
  -F            完全不读默认配置文件
  -p            打印当前生效配置
  -l / -r <num> 榜单长度        -s  按 transfer 排序
```

配置项 `EnvelopeSenderFilter` / `EnvelopeRecipientFilter` / `RelaySenderFilter` /
`RelayRecipientFilter` 的取值以 `*` 之外的内容按 XPG3/POSIX 正则编译（`-DUSE_REGEXP`），
前缀 `!` 表示取反；`test_package/` 用一份自造 sendmail 日志对该正则路径做了往返断言。

