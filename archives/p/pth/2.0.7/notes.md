# pth 2.0.7 — HarmonyOS PC 适配说明

## 概况

`pth`（GNU Portable Threads）是协作式（非抢占）线程库，产物为 `libpth.a`、
`pth.h`、`pthread.h` 与 `pth-config`。

- 上游：https://www.gnu.org/software/pth/
- 形态：autotools（2006 年的 autoconf/libtool）
- 依赖：无
- 许可证：LGPL-2.1-or-later

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | `configure` 硬编码 `/tmp` 作暂存 | 补丁改为 `${TMPDIR:-/tmp}`（OHOS `/tmp` 只读） |
| 2 | 老 `config.sub` 不认 `aarch64` | 用 `arm-unknown-linux-gnu` 三元组（pth 无架构汇编，仅 1 处 `__i386__`） |
| 3 | OHOS bionic 无 `makecontext`/`swapcontext` | 强制 `sjlj` + `sjlje` + `sas`（sigaltstack）方法 |
| 4 | `config.status` 用 mode 0700 的 `mktemp -d` 暂存目录 | HMDFS setgid 目录下 0700 不可写且 mktemp 恒 0700（umask 无效）→ 复用知识库 **E011 / DRAFT-6507-cln-mktemp-0700-hmdfs**：放弃 mktemp，改用 `umask 000 && mkdir` |
| 5 | 不支持 `make -j`（jobserver mkfifo） | 串行 `make` |
| 6 | CLI 工具门禁 | 软件级 `commands.json`；装 `bin/pth-config` |

## 测试

### 上游

`build()` 中只运行**会自行终止**的上游程序并全部通过：`make test`（`test_std`：全局库 API / 基本操作 / 基本线程 / 嵌套线程）+ `make test-mp test-misc < /dev/null`（`test_mp` 多池调度 / `test_misc` 杂项 API；两者为交互式程序，stdin 重定向到 `/dev/null` 后读到 EOF 退出）：

```
OK - ALL TESTS SUCCESSFULLY PASSED.
Pth: OK: arm-unknown-linux-gnu | sjlj/sjlje/sas | down | 2.0.7
```

### 消费者测试（test_package）

`test_package/test_pth.c`：`pth_init` → `pth_spawn` → `pth_join`，断言返回值 `42`。

## 已知限制

- 上游 7 个程序未纳入 `build()` 运行（其余 3 个已真实运行通过），逐条原因：
  `test_sig` 交互式（3x CTRL-C）、`test_select` 不退出、`test_httpd` 需网络服务器、
  `test_pthread` 本（sjlj）配置编译失败、`test_sfio` 未启用 `--with-sfio`（仅打印提示）、
  `test_uctx` 为性能基准（1000 万次上下文切换，非断言）、`test_philo` 为 60s 观测型演示（无断言）。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
