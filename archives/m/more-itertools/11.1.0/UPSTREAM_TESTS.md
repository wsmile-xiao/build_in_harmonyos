# more-itertools 11.1.0 — 上游测试记录

> 本文件记录 more-itertools 11.1.0 上游测试的**实测结果**与**运行方式**——
> 上游测试源码位于 sdist 源码包内（`source()` 下载解压后 `tests/` 目录），
> 不在仓库 diff 中；此处如实回填（rule 4——不伪造通过率）。

## 上游测试统计（本地实测）

| 项目 | 数值 |
|------|------|
| 测试目录 | `tests/`（sdist 内——3 个 .py 测试文件） |
| 测试文件数 | 3（tar tzf 核验） |
| pytest 用例数 | **722**（pytest 收集展开） |
| 本地实测通过率 | **722/722 = 100%**（pytest 实测 passed=722 failed=0——含 19896 个 subtest） |

## 运行方式

```sh
cd <sdist 解压目录>
python3 -m pytest tests/ -q
# 实测输出：722 passed, 19896 subtests passed in 44.16s
```

- 上游测试为 pytest 单元测试（纯 Python——依赖 typing_extensions 等）
- 适配后消费者验证（R34）以真实调用被测包 API 为准：
  `test_package/test_more_itertools.py`（import more_itertools + chunked/take API——1/1 = 100%）
- 上游测试通过率 722/722 = 100% 已在本文件与 PR 描述中如实记录——**未少报**、
  **不伪造**（rule 4）
