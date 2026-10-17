# DRAFT-tinydb-4.8.2-pypi-sdist-test-inventory

## 问题

PyPI 同一版本的 wheel 可只包含运行时代码，而 source distribution（sdist）另含上游测试。若 Conan recipe 只使用 wheel 或从 wheel 复制模块，就可能误记为“上游 0 测试”；应以锁定摘要后的 sdist 作为上游测试输入，再单独打包运行时模块。

TinyDB 4.8.2 的反直觉点：PyPI 标注 wheel 为 `py3-none-any`，但该标签只说明 wheel 的 Python/ABI/platform 兼容性，不保证 wheel 与 sdist 内部文件相同。此版本 wheel 有 15 个文件且 0 个 tests；sdist 则包含 7 个 pytest 模块。

## 根因

wheel 与 sdist 是分别构建的发行物，构建配置可以只将 `tests` 纳入 sdist。TinyDB 4.8.2 的 Poetry 配置明确把 `tests` 标为 `format = "sdist"`；所以从运行时 wheel 或最终 `site-packages/tinydb` 目录无法推断上游测试总数。

## 最小解决与边界

1. 从官方 PyPI 获取目标版本 sdist，校验 SHA-256 并列出归档文件。
2. 从该 sdist 根目录运行上游 suite，按实际 collected/pass/fail 数回填；不可用 wheel 的内容清单代替。
3. 运行通过后只把运行时 Python 模块、typing marker 与许可证安装进 Conan 包；测试和构建元数据留在源码/构建阶段。
4. `test_package` 再通过消费者环境导入已安装模块，单独统计鸿蒙消费者用例。

边界：并非所有 sdist 都含测试，且部分项目的 sdist 也会裁剪；每个版本都要按摘要检查实际归档。若上游只提供 wheel 且无源码测试，按 R51 找其他官方测试入口并说明原因，不能把“不在 wheel 中”推成“上游没有测试”。含 C 扩展的包也不适用纯 Python 直接复制运行时模块的方案。

## 验证

### TinyDB 4.8.2

- 官方 sdist：`tinydb-4.8.2.tar.gz`，32.6 kB，SHA-256 `f7dfc39b8d7fda7a1ca62a8dbb449ffd340a117c1206b68c50b1a481fb95181d`。
- 官方 wheel：`tinydb-4.8.2-py3-none-any.whl`，24.9 kB，SHA-256 `f97030ee5cbc91eeadd1d7af07ab0e48ceb04aa63d4a983adbaca4cba16e86c3`。
- `zipfile` 检查 wheel：15 个文件，0 个 `/tests/` 路径；`tarfile` 检查 sdist：7 个 `tests/test_*.py`。
- sdist `pytest --collect-only` 收集 204 项；HarmonyOS PC 真机 suite 全量结果 `204 passed`。默认 pytest temp root 因已有目录 owner 不匹配报错；recipe 按现有 pytest temp-root 处理经验传 recipe-private `--basetemp`，未改上游测试。
- R34 consumer test 从 Conan `conanrun` 环境导入打包后 TinyDB，执行 JSON 插入、Query 检索、计数和关闭；`conan create` 最终退出码 0。

### 独立语料 json5 0.15.0

- 官方 sdist SHA-256 `7424d1f1eb1d56da6e3d70643f53619862b4ce81440bdb8ecfd6f875e5ba4a71`；归档有 5 个 Python 测试文件。对应官方 wheel 有 0 个 tests 路径。
- HarmonyOS PC 使用同一 pytest 8.4.2 test runner 和 recipe-private basetemp 实跑其上游 `tests/`：`75 passed`。
- 两个独立 PyPI 项目均出现“sdist 有测试、wheel 没有测试”，证明打包器应先盘点精确发行归档，再确定上游测试口径。

复核命令示例：`python -c "import zipfile,tarfile; ..."`、`pytest --collect-only -q tests/`、`pytest -q tests/`。

## 七轴查重

| 轴 | 检索对象/命令 | 与本草稿的边界 |
|---|---|---|
| 工具 | `git grep -il -E 'sdist.*wheel|wheel.*sdist' origin/main -- knowledge/graph knowledge/doc` | 0 命中。 |
| 阶段 | `git grep -il -E 'PyPI.*(test|pytest)|pytest.*PyPI' origin/main -- knowledge/graph knowledge/doc` | 0 命中。本文位于上游测试输入盘点阶段。 |
| 根因 | `git grep -il -E 'source distribution.*test|test.*source distribution' origin/main -- knowledge/graph knowledge/doc` | 0 命中。根因是同版本 sdist/wheel inclusion 不同，不是 HarmonyOS ABI。 |
| 方案 | 比较 `zipfile` 的 wheel 清单与 `tarfile` 的 sdist 清单，再对 sdist 执行 pytest | 与检查安装目录/版本元数据不同，直接锁定测试源文件归档。 |
| 平台 | HarmonyOS PC 的 Conan 上游测试流程 | sdist/wheel 发行机制跨平台；结果影响 HarmonyOS task 的真实上游测试计数。 |
| 证据 | 两个 PyPI release 的 SHA、测试文件数、pytest 实跑结果 | TinyDB 204/204 与 json5 75/75 均有完整、独立源语料。 |
| 相邻条目 | `DRAFT-pyjson5-0.15.0-pure-python-no-build-packaging`, `DRAFT-VENDP-PUREPY-DEP-CLOSURE`, `E543-draft-DF80` | 前两者讨论免构建打包/依赖闭包；E543 讨论 pytest temp owner 与 runner；本文只补同版本 wheel 与 sdist 的测试文件差异和计数边界。 |

## 七轴结论

对 formal graph/doc 的三组针对性查询均为 0 命中。已合入/相邻稿件覆盖纯 Python 打包、依赖闭包和 pytest 环境，但未覆盖同一 PyPI release 的 wheel 与 sdist 具有不同测试清单这一机制。TinyDB 与 json5 两组归档及测试实跑提供独立证据，作为待审核草稿提交。

## 元信息

- 库/版本：TinyDB 4.8.2
- 上游：<https://pypi.org/project/tinydb/4.8.2/>
- 任务：#11157
- Contributor AtomGit ID：328
- 草稿状态：`draft: true`