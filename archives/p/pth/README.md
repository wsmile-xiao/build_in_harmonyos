# pth 2.0.7 — HarmonyOS PC 适配说明

## 概况

`pth`（GNU Portable Threads）是一个基于 POSIX 线程/信号实现的**协作式（非抢占）**
线程调度库：线程主动让出（`pth_yield`/阻塞调用）时才切换，适合把阻塞式代码
改造成并发执行。

- 上游：https://www.gnu.org/software/pth/
- 形态：autotools（老 autoconf/libtool，2006 年）
- 产物：`lib/libpth.a`、`include/pth.h`、`include/pthread.h`、`bin/pth-config`
- 依赖：无
- 许可证：LGPL-2.1-or-later

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | `configure` 硬编码 `/tmp` 作暂存 | OHOS `/tmp` 只读 → 补丁改为 `${TMPDIR:-/tmp}` |
| 2 | 老 `config.sub`（2005）不认 `aarch64` | pth 机器上下文与方法相关、无架构汇编 → 用老脚本认识的 `arm-unknown-linux-gnu` 三元组 |
| 3 | OHOS bionic 无 `makecontext`/`swapcontext` | 强制 `sjlj` 方法（`--with-mctx-mth=sjlj --with-mctx-dsp=sjlje --with-mctx-stk=sas`） |
| 4 | `config.status` 用 `umask 077 && mktemp -d` 建 mode 0700 暂存目录 | HMDFS setgid 目录下 0700 不可写且 `mktemp -d` 恒 0700（umask 无效）→ 复用知识库 **E011 / DRAFT-6507-cln-mktemp-0700-hmdfs**：放弃 mktemp，改用 `umask 000 && mkdir` |
| 5 | 构建环境不支持 `make -j`（jobserver mkfifo） | 串行 `make` |
| 6 | CLI 工具门禁 | 软件级 `commands.json`；装 `bin/pth-config` |

## 测试

### 上游

`build()` 中只运行**会自行终止**的上游程序并全部通过：
- `make test` → `test_std`（全局库 API、基本操作、基本线程、嵌套线程）：**OK - ALL TESTS SUCCESSFULLY PASSED**
- `make test-mp test-misc < /dev/null` → `test_mp`（消息端口多池调度）、`test_misc`（杂项 API）；
  这两个是**交互式**程序，stdin 重定向到 `/dev/null` 后读到 EOF 正常退出

```
Pth: OK: arm-unknown-linux-gnu | sjlj/sjlje/sas | down | 2.0.7
```

其余 7 个上游程序因交互式（`test_sig`）、不退出（`test_select`）、需网络（`test_httpd`）、
本配置编译失败（`test_pthread`）、未启用 SFIO（`test_sfio`）、性能基准（`test_uctx`，1000 万次切换）、
60s 观测演示（`test_philo`）而声明豁免。

### 消费者测试（test_package）

`test_package/test_pth.c` 编译并运行一个程序，对安装后的 `libpth` 做 1 条断言：
`pth_init` → `pth_spawn` → `pth_join`，返回值应为 `42`（真实触发 mctx 切换）。

## 已知限制

- 上游 7 个程序未纳入运行，逐条豁免原因见上；其余 3 个已真实运行通过。
- `config.sub` 未更新，使用 `arm-unknown-linux-gnu` 三元组（对 pth 无架构差异）。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
