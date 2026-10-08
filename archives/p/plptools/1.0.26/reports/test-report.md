# plptools 1.0.26 测试报告

测试日期：2026-10-01；目标：HarmonyOS PC aarch64；W3 事务：`plptools-w3-20260930T173000Z`。

| 类型 | 发现/执行 | 结果 |
| --- | ---: | --- |
| 上游 Automake 注册测试 | 0/0 | `make check` 无 `TESTS` / `check_PROGRAMS` |
| 安装后 CLI 消费者 | 4/4 | `ncpd`、`plpftp`、`plpprintd`、`sisinstall` 均执行 `--version` |
| 可选 FUSE 与串口硬件 | 0 | 未交付/未验证，不能声称通过 |

上游测试用例未修改。目标机运行收据 12/12，`W3_PASS`；日志 SHA-256 `2f0056d3f2d366590fe09b59b9c12ba92e4e509bc22f71de9128d72948bd048e`。
