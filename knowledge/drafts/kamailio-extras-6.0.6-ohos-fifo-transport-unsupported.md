# OHOS 禁 FIFO（SELinux）的应用级后果：kamailio jsonrpcs FIFO transport 初始化即失败

> Status: DRAFT（草稿期以文件名标识）
> Source: kamailio-extras 6.0.6 适配期间执行上游 `test/unit` 测试套件，2026-09-29
> Related: E525 / E074（同一平台属性的**构建期**后果：make 必须 `-j1`）、E292、P013

## 问题

OHOS 上用户进程**不能创建 FIFO**（SELinux 策略）。这不只影响构建工具（`make` 的
jobserver 依赖 FIFO，见 E525/E074），也直接打断**运行期**使用命名管道做 IPC 的应用：

kamailio 的 `jsonrpcs` 模块带一个 FIFO transport，模块初始化时调 `mkfifo(2)`，
在 OHOS 上返回 `EPERM`，模块初始化失败、进程启动报错。

## 现象（完整错误链，实测）

```text
ERROR: <core> [core/sr_module.c:1041]: init_mod(): Error while initializing module jsonrpcs (../../src/modules/jsonrpcs/jsonrpcs.so)
ERROR: <core> [core/sr_module.c:1041]: init_mod(): Error while initializing module jsonrpcs (.../jsonrpcs.so)
ERROR: jsonrpcs [jsonrpcs_fifo.c:72]: jsonrpc_init_fifo_server(): Can't create FIFO: Operation not permitted (mode=432)
   ↑ 由 jsonrpcs_fifo.c:218 → jsonrpcs_fifo.c:575 → jsonrpcs_mod.c:1250 逐层上抛
ERROR: error while initializing modules
```

关键点：

1. 报错 errno 是 **EPERM（Operation not permitted）**，**不是** `EACCES`/`ENOENT`
   → 与目标路径、目录权限位、父目录存在性无关；改权限、换目录、重试都不会变。
2. kamailio 进程 **exit code = 0**（这是「模块初始化失败」，不是「启动失败」）
   → 只看退出码会把失败误判为成功。
3. 同一份最小配置**去掉 `jsonrpcs` 后启动正常并写 pid** → 反向确认问题就在 FIFO 创建，
   与 pid 机制、配置路径无关。

## 判据与复现

```bash
# 1) 平台属性直接判据（期望非 0，报 Operation not permitted）
mkfifo /data/local/tmp/ohos_fifo_probe; echo "rc=$?"

# 2) 应用级复现
kamailio -E -f <cfg-with-jsonrpcs-fifo> 2>&1 \
  | grep -E "Can't create FIFO|jsonrpc_init_fifo_server|error while initializing modules"

# 3) 反证：非 FIFO 配置正常启动
kamailio -E -f <minimal-cfg> & sleep 2; test -s <pid-file> && echo OK
```

上游 `test/unit` 套件在本机执行的分布（49 个脚本：38 skip / 2 pass / 9 fail），
9 项失败中 6 项即本条（4/5/7/14/15/18.sh，依赖 `$RPCFIFOPATH`/`jsonrpcs` FIFO transport）；另 3 项（6/8/10.sh）属测试环境依赖缺失（模块不在构建子集 / kamctl python 工具链不可用），与本条无关。

## 处置（按 P013：降级而非绕过）

| 层级 | 动作 |
|---|---|
| 运行期 | 不使用 FIFO transport：`jsonrpcs` 改走其它 transport（如 TCP/HTTP 上的 JSON-RPC）或不加载该模块 |
| 测试期 | 跳过依赖 FIFO 的用例，并在报告中**登记原因**（skip + 具体技术原因）；不得静默吞错 |
| 若强依赖 FIFO 语义 | 源码层用 Unix domain socket / 普通管道等价替换（实质性适配，需补丁 + 说明理由），或把该能力标为 `env_unsupported` |

## 反例（禁止）

- 反复重试 `mkfifo`、`chmod`/`mkdir` 试图"修复"：EPERM 来自 SELinux 策略，重试与改权限无效（P013）。
- 用 `| true` / `skipIf(false)` / 忽略初始化错误继续跑：把「测试没跑」伪装成「测试通过」，
  属评审硬性不通过项（R51）。

## 与 E525/E074 的关系

同一平台属性（OHOS SELinux 禁 FIFO）的两个不同后果面：

| 条目 | 触发面 | 表现 | 处置 |
|---|---|---|---|
| E525 / E074 | **构建期**（GNU make jobserver） | 构建挂起/FIFO 报错 | `make -j1` |
| 本条 | **运行期**（应用自身 IPC） | 模块初始化失败、功能不可用 | 降级到非 FIFO transport / 标 `env_unsupported` |
