# DRAFT-14985 — OHOS PC 文件系统不支持 FIFO：GNU make jobserver 并行退化串行

> 草稿（pending-editor-review），拟提升编号由主编确认。
> 来源：popt 1.19 适配（PR #14985，任务 #14953），2026-10-08 OHOS PC 真机实测。

## 可复现症状与稳定错误签名

- `make: jobserver mkfifo: /storage/Users/currentUser/tmp/GMfifo13457: Operation not permitted`
  （popt 1.19 test_package 构建，`cmake --build ... -- -j2`，2026-10-08 conan create 日志实测）
- `/tmp` 工作目录场景：`make: jobserver mkfifo: ./GMfifo*: Read-only file system`
- 稳定错误签名（正则）：`make: jobserver mkfifo: .*(Operation not permitted|Read-only file system)`

## 根因与最小复现

- GNU make 4.x jobserver 在并行构建时通过 `mkfifo` 创建 `GMfifo<pid>` 命名管道传递并行令牌。
- OHOS PC 用户可写路径均无法创建 FIFO（真机实测，2026-10-08）：
  - HMDFS 挂载（`$HOME/tmp` 等）：`mkfifo` → **EPERM**（errno=1，Operation not permitted）
  - `/tmp`：**EROFS**（errno=30，Read-only file system）
- 最小复现（python3 一行）：

```python
import os
os.mkfifo('/storage/Users/currentUser/tmp/f')   # OSError: [Errno 1] Operation not permitted
os.mkfifo('/tmp/f')                              # OSError: [Errno 30] Read-only file system
```

- make 检测 FIFO 创建失败后**自动降级串行**，构建仍成功，但每个子 make 重复打印告警。

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| 保持 make -j2（依赖 make 自动降级） | 构建成功但告警刷屏，jobserver 探测开销残留 |
| 知识库检索 jobserver/mkfifo/GMfifo | graph + drafts 全文检索**零命中**（空白确认） |
| 配方显式 make -j1（采纳） | 告警消失，构建时序确定，conan create 全绿 |

## 最终方案、输入输出与真实验证

- 输入：任何在 OHOS PC 上以 GNU make 并行构建的配方（autotools `make -jN` / CMake `cmake --build -- -jN`）。
- 处理：配方层显式 `-j1`（`autotools.make(args=["-j1"])`）；或接受自动降级（仅告警）。
- 输出：无告警的确定性串行构建。
- 真实验证：
  - popt 1.19（PR #14985）：`conan create -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
    全绿（configure → make -j1 → install → test_package 1/1 PASS）；
  - 上游测试套件 `tests/testit.sh` 65/65 全通过（62x test1 + 3x test3 diff）；
  - popt 1.16（PR #3275 已合入）同款 `-j1` 先例（notes 记录 "HarmonyOS 不支持 mkfifo，使用 make -j1"）。

## 跨库复用面

- 所有 autotools 包（本仓库主力形态）的 conanfile make 调用
- 所有 CMake 包的构建与 test_package（`cmake --build` 默认传 -j 场景）
- CI worker 与本地构建同样适用（同一 HMDFS/EROFS 文件系统语义）

## 查重与覆盖判断

- 查重关键词：jobserver / mkfifo / GMfifo / FIFO / Operation not permitted / 串行
- 覆盖判断：`knowledge/graph/` 与 `knowledge/drafts/` 全文检索零命中。
  相邻条目：E248（patch 顺序 mtime 触发 automake 重生成）、E041/E071（automake 版本不匹配）、
  E129（HMDFS setgid umask）——均为相邻但不同主题；本条增量在
  「FIFO 缺失 → make 并行机制退化」这一文件系统能力维度的平台差异及其配方层对策。
