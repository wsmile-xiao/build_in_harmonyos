# tlog

tlog 是 Red Hat 出品、现由 Scribery 维护的**终端会话录制与回放**工具，
把终端 I/O 录成 JSON 流，用于审计、合规检查与问题复现。

- 上游：https://github.com/Scribery/tlog
- 许可：GPL-2.0-or-later
- 本仓适配版本：14（HarmonyOS PC / OHOS aarch64）

## 交付内容

| 路径 | 内容 |
|------|------|
| `bin/tlog-rec` | 录制定长命令的终端 I/O 到日志 |
| `bin/tlog-rec-session` | 录制整个用户会话（可作登录 shell） |
| `bin/tlog-play` | 回放录制日志（终端 / Elasticsearch / 文件） |
| `bin/tlog-rec-session-shell` | 会话包装脚本（上游辅助脚本） |
| `lib/libtlog.a` | 库（默认静态；`-o shared=True` 时产 `libtlog.so`） |
| `include/tlog/*.h` | 公开头（grc / pkt / json 流 / utf8 / timestr 等） |
| `share/tlog/*.default.conf` | 上游默认配置（**运行时必需**） |
| `etc/tlog/*.conf` | 本地配置（**运行时必需**） |

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| [json-c](https://github.com/json-c/json-c) | 0.18 | 录制流 JSON 编解码（configure 必备） |
| [curl](https://curl.se/) | 8.15.0 | 回放/录制写入 Elasticsearch（configure 必备） |

## 使用

```sh
conan install --requires=tlog/14 -r=ohpcd
```

运行时注意（上游行为，非本适配引入）：`tlog-rec` / `tlog-play` /
`tlog-rec-session` 启动时会**同时**要求默认配置与本地配置存在，缺一即
`rc=1` 并报 `Failed loading default configuration` /
`Failed finding system configuration`。配置查找路径按「二进制自身的真实路径」
判定（`lib/tlog/misc.c:44`）：

| 二进制位置 | 默认配置 | 本地配置 |
|-----------|----------|----------|
| 目录名为 `.libs`（libtool 构建树） | `<exe_dir>/../<prog>.default.conf` | `<exe_dir>/../<prog>.conf` |
| 其它（安装态） | 编译期路径 `/share/tlog/<prog>.default.conf` | `/etc/tlog/<prog>.conf` |

```sh
# 安装态（prefix=/）：
#   /bin/tlog-rec 使用 /share/tlog/tlog-rec.default.conf + /etc/tlog/tlog-rec.conf
tlog-rec --help              # 用法
tlog-rec --configuration     # 打印生效配置（JSON）
tlog-rec -o rec.log -- /bin/sh -i     # 录制一个交互 shell
tlog-play -i rec.log -- /bin/sh       # 回放（需 tty）
```

## 本仓适配说明

- 10 个平台补丁：config.guess/config.sub 识别 `aarch64-unknown-linux-ohos`
  （E007）、configure 的 `umask 077`→`022`（E114/HMDFS）、7 个公开头补最小
  POSIX 类型声明（musl/OHOS 未连带声明 `struct timespec` 等）。详见
  `14/notes.md` 与 `14/patches/`。
- 上游测试集（`src/tltest`，13 项）由配方 `build()` 内 `make check` 保留执行，
  未修改；另有 3 个消费者侧补充测试（libtlog API 探针 18 断言 + OHOS/musl 头自包含
  7 断言 + 三个 CLI 的 `--version/--help/--configuration` 7 断言）。实测数据见
  `14/reports/test-report.md`，测试清点见 `14/test_package/MANIFEST.yml`。
  其中「头自包含」为鸿蒙特有回归：同一组编译命令在未打补丁的上游源码上只有
  2/7 通过，本包打补丁后 7/7（见 test-report §3）。
