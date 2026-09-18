# procenv

> 系统/进程环境属性**探测工具**：一次性转储进程、CPU、内存、limits、sysconf、pathconf、
> uname、时钟、网络接口、文件描述符、cgroup、namespace、能力等大量信息。

## 简介

procenv 用来在**新平台**上快速摸清"这个系统提供了什么、缺什么"。它按 section 输出
（`--process`、`--cpu`、`--memory`、`--limits`、`--sysconf`、`--network`、`--capabilities` …），
并支持 `text`/`json`/`xml`/`crumb` 四种格式，适合做能力盘点与移植前侦察。

## OHOS 适配要点

| 项 | 说明 |
|----|------|
| 三元组 | configure 预生成且 `config.guess` 不认 HarmonyOS → 显式 `--build/--host=aarch64-unknown-linux-ohos`（E007） |
| HMDFS | autoconf `config.status` 的 `umask 077` 临时目录在 HMDFS 上不可用 → 补丁放宽为 `022`（E011） |
| 能力探测误判 | OHOS 的 `<sys/capability.h>` 是 48 行的裁剪内核头，**不含 libcap API**，`AC_CHECK_HEADERS` 会误通过 → `ac_cv_header_sys_capability_h=no` |
| musl 差异 | `major/minor` 需要 `<sys/sysmacros.h>`；无 `pthread_getconcurrency`；无 `pthread_getaffinity_np`（退回 `sched_getaffinity`） |
| 用户信息 | OHOS 的 `/etc/passwd` 只有 root/bin/system，进程 uid 查不到 → 降级为"未知用户"而非中止 |

### 已知平台限制（非 procenv 缺陷）

- **`-b/--libs` 与 `-i/--misc` 会忙等挂起**（持有 AF_INET socket 自旋），因此
  **无参数全量 dump 也会挂起**。实测：`timeout 3 procenv -b` / `-i` → 超时；其余节正常。
- 上游 `check_pr_list`（libcheck，7 用例）**已可执行**：libcheck 的临时目录顺序是
  `TEMP` > `P_tmpdir`（编译期 `/tmp`）> `TMPDIR` > `.`；因 `P_tmpdir` 优先且 `/tmp` 只读，
  必须设 **`TEMP`** 指向可写目录（本包在 `build()` 中已设置），实测 `100%: Checks: 7, Failures: 0`。

> 因此使用建议：调用 `procenv` 时**指定具体 section**（如 `--uname`、`--limits`、`--environment`），
> 不要调用 `-b/--libs`、`-i/--misc` 和无参数全量 dump。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| （运行） | - | 无 |
| check | 0.15.2 | 仅构建期 `test_requires`，用于编译上游 `check_pr_list`（未传播） |

## 使用

```bash
procenv --version
procenv --format=json --uname          # JSON 输出，便于程序解析
procenv --format=xml  --sysconf
procenv --limits
procenv --environment
```

## 参考

- [上游仓库](https://github.com/jamesodhunt/procenv)
- `share/man/man1/procenv.1`
