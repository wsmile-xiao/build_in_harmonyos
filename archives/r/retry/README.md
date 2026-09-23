# retry

`retry` 重复执行给定命令直到满足条件（默认直到成功），用于把不稳定操作（网络请求、资源就绪等待等）包装成可靠的一步。它会：

- 把 **stdin 捕获进内存**，并在每次重试时重放给被重复的命令，因此可以直接嵌入 shell 管道；
- 把 **stdout 缓存**，仅当命令成功时把 stdout 正常输出；被重试（失败）尝试的 stdout 改道到 stderr，保证 stdout 只输出一次。

上游 [github.com/minfrin/retry](https://github.com/minfrin/retry)（作者 Graham Leggett，Apache-2.0）。

## 功能概述

- `retry [-v] [-h] [-u until] [-w while] command ...`
  - `-u/--until`：重复直到满足条件（`success`/`true`/`fail`/`false`、整数、整数区间，可逗号分隔，默认 `success`）
  - `-w/--while`：只要仍满足条件就继续重复
  - `-t/--times`：最多尝试次数（默认无限重试）
  - `-d/--delay`：每次重试的退避秒数（支持逗号分隔的递增序列，最后一个重复），`-j/--jitter` 追加随机抖动
  - `-m/--message`：自定义退避通知中的命令名
- 退出码 = 被重复命令最后一次的退出码；无法执行/参数非法返回 1；被信号中断返回 128+信号

## 依赖关系

- 编译依赖：无（单文件 ANSI C + POSIX，仅链接系统 libc；Autotools 构建）
- 运行依赖：无

## OHOS 适配要点

- 官方 release tarball 自带生成的 Autotools 树，`configure` + `make` 即可用 OHOS SDK clang（aarch64-linux-ohos）构建
- 补丁 0001/0002：2018 年版 `config.guess`/`config.sub` 不认识 HarmonyOS 与 `linux-ohos` 三元组——分别补 HarmonyOS 分支与 `linux-ohos*` 模式（native 构建走 config.guess，交叉构建走 config.sub），纯可移植性修复、无平台宏
- 补丁 0003：configure 的 config.status 临时目录由 `umask 077` 放宽为 `022`，规避 HMDFS UID 映射导致的目录不可写（知识 E011）
- 上游 1.0.6 无测试套件；`test_package/test_retry.sh` 补 28 条消费侧功能断言（真实执行已安装二进制），清点证据见 [1.0.6/test_package/MANIFEST.yml](1.0.6/test_package/MANIFEST.yml)

## 参考资料

- 上游仓库：<https://github.com/minfrin/retry>
- 手册（man）：`share/man/man1/retry.1`
- 发行包：<https://github.com/minfrin/retry/releases/tag/retry-1.0.6>

## 版本

- `1.0.6` — 适配 HarmonyOS PC（aarch64-linux-ohos / armv8）；3 个可移植性补丁；见 [1.0.6/notes.md](1.0.6/notes.md)

## 产物

| 路径 | 说明 |
|------|------|
| `bin/retry` | 主程序（arm64 ELF） |
| `share/man/man1/retry.1` | man 手册 |
