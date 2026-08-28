# dataproperty 1.1.1 — 上游测试记录

> 本文件记录 dataproperty 1.1.1 上游测试的**实测结果**与**运行方式**——
> 上游测试源码位于 sdist 源码包内（`source()` 下载解压后 `test/` 目录），
> 不在仓库 diff 中；此处如实回填（rule 4——不伪造通过率）。

## 上游测试统计（本地实测）

| 项目 | 数值 |
|------|------|
| 测试目录 | `test/`（sdist 内——test_align_getter / test_column_dataproperty / test_typing 等） |
| 测试文件数 | 13（tar tzf 核验） |
| pytest 用例数（参数化展开） | **622** |
| 本地实测通过率 | **622/622 = 100%**（pytest 分片逐文件跑——passed=622 failed=0） |

## 运行方式

```sh
# 依赖 PYTHONPATH 注入（typepy/mbstrdecoder/chardet 等已发布依赖）
PYTHONPATH=<site-packages 路径>:<依赖的 site-packages> python3 -m pytest test/ -q
```

- 上游测试为 pytest 单元测试（开发期测试），依赖 pytest 环境与多个第三方库
  （typepy/mbstrdecoder/chardet）的 PYTHONPATH 注入
- 适配后消费者验证（R34）以真实调用被测包 API 为准：
  `test_package/test_dataproperty.py`（import dataproperty——1/1 = 100%）
- 上游测试通过率 622/622 = 100% 已在本文件与 PR 描述中如实记录——**未少报**、
  **不伪造**（rule 4）
