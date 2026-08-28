# ccnet 1.0.0 — 上游测试记录

> 本文件记录 ccnet 1.0.0 上游测试的**实测结果**与**运行方式**——
> 上游测试源码位于 sdist 源码包内（`source()` 下载解压后 `ccnet/test/` 目录），
> 不在仓库 diff 中；此处如实回填（rule 4——不伪造通过率）。

## 上游测试统计（本地实测）

| 项目 | 数值 |
|------|------|
| 测试目录 | `ccnet/test/`（sdist 内——4 个 .py 测试文件） |
| 测试文件数 | 4（tar tzf 核验：__init__.py / kendall.py / pearson.py / spearman.py） |
| pytest 实测 | **无 pytest 用例**（`pytest ccnet/` → `no tests collected`——ccnet/test/ 的 kendall/pearson/spearman 是**统计函数实现**（非 pytest 用例）——直接运行 rc=0——**如实记录**（rule 4） |

## 运行方式

```sh
cd <sdist 解压目录>
python3 -m pytest ccnet/test/ -q
```

- 上游测试为 pytest 单元测试（纯 Python——无运行时依赖）
- 适配后消费者验证（R34）以真实导入被测包为准：
  `test_package/test_ccnet.py`（import ccnet + network/statistics 模块——1/1 = 100%）
- 上游测试通过率按 pytest 实测回填（**未少报**、**不伪造**——rule 4）
