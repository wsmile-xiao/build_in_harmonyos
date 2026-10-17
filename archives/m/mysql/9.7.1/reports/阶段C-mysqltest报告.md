# MySQL 9.7.1 OHOS 适配 —— 阶段C：轻量 mysqltest 报告

> **更新（2026-09-15）**：本报告"mysqltest 无法执行"的结论已被推翻——服务端已在 OHOS 上正常启动
> （补丁 0068 `patches/0068-ohos-runtime-sandbox-fixes.patch` 修复 HMDFS 大小写折叠与沙箱
> fallocate / AF_UNIX bind 限制），上游 `testclients/mysql_client_test` 315 项已真实执行（307 通过）。
> 仍需完整 MTR 框架（perl 驱动 + Unix socket 通信）的 9339 个 `.test` 未运行，原因见
> `reports/上游测试-testclients执行报告.md` 第 5 节。

日期：2026-09-10

## 结论

**mysqltest 抽样无法在本机执行**，原因与阶段B 完全一致（mysqld 无法在 OHOS 沙箱内完成启动），如实记录如下。

## 尝试与依据

1. mysqltest-run 需要先启动一个可用的 mysqld 实例（本机模式 `--start-and-exit` 也依赖 datadir 初始化 + socket 通信）。
2. 本机 mysqld 生命周期阻塞点：
   - `fallocate` syscall 被 OHOS seccomp 拦截（EPERM），InnoDB DD 中 undo 表空间注册不完整，正常启动报
     `Can't create UNDO tablespace innodb_undo_00X since './undo_00X' already exists`；
   - `--innodb-force-recovery=6` 可越过该步，但随后 unix socket `bind()` 同样返回 EPERM，服务无法监听。
3. 因此 main 套件抽样（planned：main.1million 等轻量用例）无法运行。

## 计划抽样清单（未执行）

| 用例 | 预期耗时 | 说明 |
|------|---------|------|
| main.1million | 轻量 | 基准轻量用例 |
| main.create | 轻量 | DDL 基础 |
| main.insert | 轻量 | DML 基础 |
| main.select | 轻量 | 查询基础 |

## 下一步建议

- 在不受 OHOS seccomp 限制的宿主机（标准 Linux aarch64 或真机环境）上完成 mysqltest 抽样。
- 或允许 seccomp 放行 `fallocate`/`socket` 后重跑。
- 相关证据见 `阶段B-测试报告.md`。