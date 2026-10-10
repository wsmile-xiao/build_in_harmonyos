# pd-log（Small Pure Data library for logging）

`pd-log` 是 IOhannes m zmölnig 写的 [Pure Data](https://puredata.info) 日志库，
提供 5 个 externals：`[logpost]`（通用，按 level 过滤）、`[fatal]`（level 0）、
`[error]`（level 1）、`[normal]`（level 2）、`[debug]`（level 3）。
每个对象都是 `[print]` 的 drop-in 替身，只是输出可以按 verbosity 过滤。

## 用法

externals 装在**本包自己的** `lib/pd-externals/log/` 下，Pd 靠 `-path` 找到它们：

```sh
pd -path <pd-log 包前缀>/lib/pd-externals
# 之后补丁里就可以用 [logpost]、[fatal]、[error]、[normal]、[debug]
```

它们不会自动落进 `puredata` 包的 `lib/pd-externals/`，必须显式把本包目录交给 Pd。

## OHOS 适配要点

- 上游只有 stock 的 Pd "Makefile template" 1.0.12，**零补丁**。
- `m_pd.h` 等 Pd API 头文件来自 `puredata/0.54.1`，用 make 命令行变量
  `PD_PATH=<puredata 包目录>` 覆盖模板里硬编码的 `PD_PATH=/usr`。
- 模板在 `uname=Linux` 分支已选中 `.pd_linux` 后缀，这正是 Pd 在 OHOS 上加载
  externals 用的后缀，所以不需要引入任何平台宏。
- `objectsdir` 只传父目录（`/lib/pd-externals`）：install 规则会自己追加库名。
- `STRIP=:`：install 规则里的 `strip` 会让 OHOS clang wrapper 写入的 ELF
  code signature 失效。
- externals **不链接 libpd**：只导出 `<name>_setup` 并导入 `logpost(3)`，
  后者由运行中的 Pd 进程在 `dlopen` 时提供；`NEEDED` 只有 `libc.so`。

## 交付物

| 路径 | 内容 |
|------|------|
| `lib/pd-externals/log/*.pd_linux` | 5 个 externals（aarch64 ELF64 共享对象） |
| `lib/pd-externals/log/*-help.pd` | 5 个帮助补丁 |
| `lib/pd-externals/log/log-meta.pd` | 库元信息（`VERSION 0.1`） |
| `lib/pd-externals/log/README.txt` / `LICENSE.txt` | 上游随包文档与许可 |
| `licenses/LICENSE.txt` | 许可证副本 |

本包不含可执行文件（externals 是 `dlopen` 插件），因此不需要 `commands.json`。

## 许可

- 源码与元信息：<https://download.puredata.info/log>
- 许可证：Standard Improved BSD License（见包内 `LICENSE.txt`）