# DRAFT：挂载不可用平台上的 FUSE 消费端测试构造（可审计版）

- **id**: `DRAFT-mhddfs-0.1.39.0-fuse-consumer-test-construction`
- **来源**: mhddfs 0.1.39.0 适配（test_package 实跑 10/10）
- **平台**: HarmonyOS PC / OpenHarmony aarch64（普通进程 FUSE 挂载不可用）
- **日期**: 2026-09-27

## 一类问题

FUSE 消费端的上游测试（示例：mhddfs `tests/` 7 helper + Makefile 10 个挂载类目标，共 17 项）
**全部以 live mount 为前提**。当平台不允许普通进程挂载时：

- 照搬上游 → 0/17 全量阻塞；
- 写"只打印不执行二进制"的空壳测试 → R34/PF3 拦截，CI L1e 破坏性反测（移走
  `bin/` 后重跑 `conan test`）会当场击穿；
- 把挂载断言改成 skip 以美化通过率 → 欺骗性行为（R9/R51）。

正确构造是三层组合（本仓 mhddfs 实例已实跑验证）：

## 构造要点

**① 硬断言：打包后二进制的可确定行为（不依赖挂载）**

以 mhddfs 的 `test_package/test_mhddfs.py` 为例（10 项断言全过）：

- `--version` / `-V`：输出 `mhddfs version: 0.1.39.0` 且 rc=0；
- 无参数 / 单参数：输出 `Usage:` 且 rc≠0；
- 不存在的源目录：输出 `can not stat` 诊断且 rc≠0；
- 非目录参数：输出 `is not directory` 诊断且 rc≠0；
- 重复源目录：输出 `Duplicate directories … excluded from dirlist`（启动即去重）；
- `-o mlimit=64m`：输出 `move size limit 67108864 bytes`（选项解析真实性）；
- 启动信息：逐目录 `directory '…' added to list` + `mount to: …`。

这些断言真实执行被测二进制、真实读取其输出，覆盖参数解析/目录校验/聚合选项等
**上游核心启动路径**，不是空壳。

**② 有界双向判定：真实挂载尝试（唯一依赖平台能力的项）**

```python
try:
    run([...], timeout=20)          # fuse_main 挂载成功时停留前台 → TimeoutExpired
except TimeoutExpired:
    fusermount -u / umount 目标      # best-effort 清理；记为"平台支持 FUSE"
else:
    必须 rc≠0 且输出含 "fuse" 诊断   # OHOS 现状：干净边界失败
```

无论走哪条支路都必须在报告中**如实记录实际支路**；超时上界防挂死，清理命令尽力执行。

**③ 上游测试逐项 BLOCKED 申报（R51）**

对每个上游 helper/Makefile 目标给出具体技术原因（live mount 前提、pkg-config fuse、
gcc、/sbin 工具、loop 设备或 sudo 等），在 `reports/test-report.md` 与 PR 正文如实
回填"0 可运行 / 17"，附原始尝试输出；**不改写为 skip、不删除**。

## 与现有条目的差异化

- 与 `DRAFT-mhddfs-0.1.39.0-ohos-fuse-consumer-mount-boundary` 配套：前者答
  "为什么挂不了"（平台边界），本条答"挂不了时测试怎么写"（质量构造）。
- 与 `DRAFT-cohomcalg-0.32-cli-help-rc1-test`（CLI 退出码测试）相比，本条补齐了
  **平台能力依赖项的双向判定**与**上游测试 BLOCKED 申报口径**。
- 与 `DRAFT-ohos-syscall-capability-matrix-fork-probe`（能力矩阵探测）相比，本条
  是测试工程方法论，不涉及具体 syscall 语义。
