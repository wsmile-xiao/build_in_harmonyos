# OHOS 真机（DAYU200）测试约束：工具面、hdc 推送/退出码、静态链接与单设备排队

> 草稿（DRAFT）— 来自润和 DAYU200-RK3568（OpenHarmony 6.0.0.47 / API20 / aarch64 / 64 位）
> 真机自动化接入、libbrotli 1.1.0 回环测试与 libalkimia 8.2.1 消费者端到端（23/23）
> 的真实踩坑记录。随 PR !13837（libalkimia 8.2.1）交付。
> 与 `.kv` 同 stem 配对，字段见 `knowledge/drafts/DRAFT-ohos-dayu200-device-test-constraints.kv`

## 问题

把交叉编译出的测试程序推到真机执行时，会连续撞上四类与环境强绑定的失败，
每一类看起来都像“测试本身有问题”，实际都是设备/链路的约束：

| 症状 | 根因 |
|---|---|
| `awk: not found` / `python3: not found` / `curl: not found` | 设备用户态是 busybox/toybox 精简工具集 |
| `hdc file send` 静默失败（PUSH_FAIL） | Windows `hdc.exe` 不认 WSL 路径（`/mnt/d/...`） |
| 退出码出现 2 / 127 等异常值 | Windows hdc 输出带 CRLF，污染 `$?` 解析 |
| `error while loading shared libraries: libbrotlienc.so` | 交叉编译默认共享链接，设备无该私有 `.so` |

## 根因与对策

### 1. 设备工具面：只有 busybox/toybox 基础工具

设备**没有** `awk`、`curl`、`python3`。因此设备侧脚本只能用
`sh`/`cmp`/`ls`/`sed`/`tr`/`mkdir`/`chmod`/`cat` 这些基础工具与 shell 内建。
例如 brotli 回环测试的设备脚本（`run_test.sh`）：

```sh
#!/bin/sh
set -e
cd /data/local/tmp/ohpc_test/brotli_test
./brotli -q 11 text.txt -o text.br
./brotli -q 5  rand.bin  -o rand.br
./brotli -d text.br -o text.back
./brotli -d rand.br -o rand.back
cmp text.txt text.back && echo "TEXT_ROUNDTRIP:OK"
cmp rand.bin rand.back && echo "BINARY_ROUNDTRIP:OK"
echo "ALL_TESTS_PASSED"
echo '{"tests": ["text_roundtrip", "binary_roundtrip"], "result": "PASS"}' > _result.json
```

需要 `awk` 等工具才能做的解析/断言，应前移到宿主侧预计算，设备上只做“执行 + 基础断言”。

### 2. hdc 推送路径与 CRLF 退出码

- **路径**：`hdc.exe` 是 Windows 程序，不识别 WSL 路径。产物必须先落到
  `D:\OHDev\device_stage\<job>\`，再用 `hdc file send D:\... <remote>` 推送。
- **退出码**：Windows hdc 的 shell 输出带 `\r`，直接取 `$?` 会得到假值（2/127）。
  执行器统一 `tr -d '\r'`，并让设备端返回显式哨兵：

  ```bash
  out=$(H shell "cd $remote && $cmd 2>&1; echo __RC__\$?" 2>&1 | tr -d '\r')
  rc=$(echo "$out" | tail -1 | sed 's/.*__RC__//' | tr -dc '0-9')
  ```

- 推送后必须 `chmod -R 755 $remote`，并以 `sh <script>` 方式执行，避免依赖可执行位。

### 3. 静态链接

设备不保证携带你刚编出来的私有 `.so`。测试二进制应静态链接
（CMake `-DBUILD_SHARED_LIBS=OFF`，或 profile `tools.build:exelinkflags=["-static"]`），
做到自包含。实测 brotli CLI 33 KB 静态产物在设备上 q11/q5 压缩 + 解压 + `cmp` 全部通过。

### 4. 单设备串行（flock）

只有一台真机，`device_runner.sh` 用全局 `flock` 排他锁把
“上传 → 执行 → 取证”整段串行化；测试目录按 `<lib>_<用途>` 命名，避免不同任务互踩
`/data/local/tmp/ohpc_test/<job>/`。

## 执行器接口（device_runner.sh v3）

```bash
device_runner.sh check                              # 就绪检查，打印 DEVICE:READY serial=...
device_runner.sh shell '<cmd>'                      # 直接执行设备命令
device_runner.sh run <job> <localdir> "<cmd...>"    # 上传 → 执行 → 采集退出码与证据
```

证据文件 `_device_evidence.json` 记录：`job`、`device_serial`、`system`、
`command`、`exit_code`、`timestamp`。

## 实测证据（libbrotli 1.1.0）

```
TEXT_ROUNDTRIP:OK        文本压缩/解压回环 ✓
BINARY_ROUNDTRIP:OK      200KB 随机二进制回环 ✓
ALL_TESTS_PASSED  exit=0
```

产物：`aarch64-unknown-linux-ohos-clang` 静态链接 brotli CLI；
证据：`_device_evidence.json` 的 `exit_code=0`。

## 实测证据（libalkimia 8.2.1 消费者端到端，随 PR !13837 交付）

同一条约束在 libalkimia 8.2.1 上换了一种形态被再次验证：Qt6/KF6 闭包无法静态化，
于是走本条的 fallback 分支（推送 `.so` 闭包 + `LD_LIBRARY_PATH`），四条约束一条没少：

- **推送路径 / 退出码**：34 个 aarch64 库 + 二进制（75 MB）平铺到
  `/data/local/tmp/ohpc_test/libalkimia_e2e/`；执行统一走 `sh run.sh`，
  退出码由哨兵回收（最终 `EXIT_CODE=0`，不是 2/127 假值）。
- **设备工具面**：设备脚本 `run.sh` 只用 `sh`/`mkdir`/`export`/`cd`，
  没有任何 `awk`/`curl`/`python3`。
- **库依赖**：Qt6/KF6 无法静态链接，改用「闭包解析 + `patchelf --replace-needed`
  归一化路径型 `DT_NEEDED` + `LD_LIBRARY_PATH=<payload>:/system/lib64`」——
  OHOS musl 不按 `LD_LIBRARY_PATH` 解析路径型 NEEDED，必须先归一化为裸 basename。
- **单设备串行**：整段推送 → 执行 → 取证在全局 `flock` 内完成，证据 JSON 由设备侧写入。

真机原始输出（节选，完整 23 行 ok）：

```
== payload files: 37 ==
== LD_LIBRARY_PATH=/data/local/tmp/ohpc_test/libalkimia_e2e:/system/lib64 ==
ok 01 1.1 parse 'x1.234,568 EUR' (comma decimal) -> 154321/125
ok 12 1.12 comparison operators (>, <, !=, ==)
ok 20 2.8 remove -> store entries gone
ok 23 3.3 launch() with unknown source returns false (no download)
RESULT: 23 checks, 0 failures
ALL_CONSUMER_TESTS_PASSED
EXIT_CODE=0
```

证据：`_device_evidence.json`（`job=libalkimia_e2e`、
`device_serial=450100445634303332018f3e7d2dba00`、
`system=OpenHarmony 6.0.0.47 (API20, aarch64, 64bit)`、`command=sh run.sh`、
`exit_code=0`、`timestamp=2026-09-29T20:13:57+08:00`），归档于
`archives/l/libalkimia/8.2.1/reports/device-e2e-evidence.md`。

## 禁止策略

- 禁止在设备脚本里使用 `awk`/`curl`/`python3`（设备不存在这些命令）。
- 禁止把 WSL 路径直接交给 `hdc file send`（必须先暂存到 D: 盘）。
- 禁止多个任务并发跑同一台设备而不加锁。
- 禁止把动态链接的测试程序当作“可直接在设备运行”的默认形态。

## 适用边界 / 反例

- 适用于 DAYU200 这类 busybox 用户态的 OHOS 设备；若设备上装了完整的 hnp/命令包，
  工具面会不同，应先用 `device_runner.sh check`/`shell` 实测再决定脚本写法。
- 若测试确实需要私有共享库，可改为推送 `.so` + `LD_LIBRARY_PATH`，但那会增加
  链路复杂度，静态链接仍是首选。
- 本条的“替代 musl 运行根 + qemu”是本机预验证手段，不能替代真机结论。

## 查重（七轴）

- `exact_duplicate`：否 — 图谱无“OHOS 真机测试约束集合”条目
- `causal_duplicate`：否 — 与 E540（设备侧 PATH 缺 `/data/service/hnp/bin`）同属“设备环境差异”，
  但 E540 是 PATH 配置问题，本条是工具面/链路/链接方式/并发四类约束
- `trigger_overlap`：部分 — `hdc`、busybox、设备路径类触发词与既有条目重合
- `solution_overlap`：部分 — 与 toybox/bats 类“设备侧运行 shim”条目同族
- `combination_novelty`：有 — 把“工具面 + 推送 + 退出码 + 静态链接 + 排队”合成一条可复用清单
- `boundary_novelty`：有 — 明确区分“必须设备侧做”与“应前移到宿主侧”的工作
- `test_migration_novelty`：有 — 给出可复制的 device_runner 流程与证据 JSON 契约

## 相关

- `similar_to`：E540、DRAFT-util-linux-ts-runsh-ohos-bash-xargs-driver、DRAFT-bats-suite-ohos-runtime-shims
- `principles`：P-LINKAGE-001（静态库优先）、P-BUILD-001（平台限制降级而非绕过）、
  P-ENV-001（环境变量语义冲突）
