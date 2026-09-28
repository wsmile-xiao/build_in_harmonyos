# DRAFT: 上游 CLI 工具无参数解析时的 test_package 验证方式

**触发**：gupnp-tools 0.12.4（HarmonyOS PC）适配 —— `conan create` 卡在 test 阶段不返回。

## 问题

上游 `gupnp-event-dumper` 的 `main()` **没有任何参数解析**（无 `GOptionContext`）：

```c
int main (int argc, char *argv[]) {
        g_autoptr (GUPnPContextManager) cm = gupnp_context_manager_create (0);
        g_autoptr (GMainLoop) loop = g_main_loop_new (NULL, FALSE);
        ...
        g_main_loop_run (loop);   /* 永久阻塞 */
        return 0;
}
```

因此在 `test_package` 里执行 `gupnp-event-dumper --help` **不会退出**：`conan create`
永久卡在 test 阶段（实测进程 35 分钟不返回），最终被超时判负——现象像"构建失败"，
真实原因是**测试入口选错**。

## 一类问题的通用判定

工具集类上游里，CLI 是否"跑一次就退出"决定了 test_package 的写法：

| 情形 | 特征 | 推荐冒烟入口 |
|------|------|--------------|
| 有 `GOptionContext`/getopt | `--help` 打印用法后 exit 0 | `--help`（最稳）；若支持"跑一次就退出"的选项（如 `gssdp-discover -n 1`）优先用它做**真实功能性**冒烟 |
| 无参数解析、常驻主循环 | 直接 `g_main_loop_run()` / `while(1)` | **有界运行**：后台启动 → `sleep N` → `kill -TERM` → `wait`，断言退出码 0 |

有界运行命令（不依赖 `timeout`）：

```bash
"$BIN" & p=$!; sleep 3; if kill -0 $p 2>/dev/null; then kill -TERM $p; fi; wait $p; exit $?
```

上游一般注册了 `SIGINT/SIGTERM → g_main_loop_quit`，故干净退出码为 0；崩溃 / 库解析失败 /
提前退出时 `wait` 返回非 0，测试自然失败。**不要**用 `timeout` 的返回码做断言：超时返回
124，无法区分"正常常驻"与"卡死"。

## 证据（本次实测）

```
gssdp-discover --help                    -> rc=0（打印 Usage: gssdp-discover [OPTION…] ...）
gssdp-discover -n 1                      -> rc=0（Using network interface ancowlan0 / Scanning ...）
gupnp-event-dumper（3s 后 SIGTERM）      -> rc=0（干净退出）
gupnp-event-dumper --help                -> 永久阻塞（修复前）
```

## 适用范围

任何 **application 型 conan 包**（产物为 `bin/` 可执行文件）的 `test_package`
冒烟设计，尤其是常驻型 CLI/守护进程工具（打印/监听/服务类）。
