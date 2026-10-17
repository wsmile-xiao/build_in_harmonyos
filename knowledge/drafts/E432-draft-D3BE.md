# DRAFT E432 — 上游测试目录名是单数 `test/` 且含两套框架（pytest + lit/filecheck）

- **条目主题**：纯 Python 包接入上游测试时的两个常见陷阱叠加：① 测试目录名不是惯例的
  `tests/` 而是单数 `test/`；② 上游 CI 同时跑 **pytest** 与 **lit/filecheck** 两套框架。
  再叠加 ③ PyPI sdist 不含测试、④ 测试要用到未随 wheel 发布的包外模块（`snitch`）。
- **状态**：草稿（待知识库主编审核提升编号）
- **关联**：riscemu 2.2.7 适配（`archives/r/riscemu/2.2.7`）、E429 / E430 / E431（同批）

## 症状

```text
$ python3 -m pytest tests/ -q
ERROR: file or directory not found: tests        # ← 目录其实叫 test/

$ tar tzf riscemu-2.2.7.tar.gz | grep -c '/test/'      # 0（PyPI sdist 里没有测试）
$ tar tzf v2.2.7.tar.gz | grep -c 'test/'              # >0（GitHub tag archive 有）

$ python3 -m pytest test/ -q                            # 49 passed
$ lit --timeout=5 -v test/filecheck                     # 11 passed（另一套框架，单跑 pytest 会漏掉）
```

## 根因与事实（riscemu 2.2.7 实测）

| 事实 | 证据 |
| --- | --- |
| PyPI sdist 不含测试 | `riscemu-2.2.7.tar.gz` sha256 `9f206b19…c499`，无 `test/` 条目 |
| GitHub tag archive 含测试 | `v2.2.7.tar.gz` sha256 `d9d4da9b…bd0c`，含 `test/*.py` 与 `test/filecheck/` |
| 目录名是单数 `test/` | `test/{test_RV32F,test_float_impl,…}.py` + `test/filecheck/*.asm` |
| 上游跑两套框架 | `.github/workflows/ci-pytest.yml`：`pytest -W error` **与** `lit --timeout=5 -v test/filecheck` |
| `snitch/` 不随 wheel 发布 | `pyproject.toml` 的 poetry `packages` 只含 `riscemu`；而 `test/filecheck/snitch/*.asm` 需要 `python3 -m snitch` |
| lit 的 cwd 依赖源码树 | `test/filecheck/lit.cfg`：`xdsl_src = dirname(dirname(test_source_root))`，`ShTest(preamble_commands=[f"cd {xdsl_src}"])` |

## 修复（接入方案）

1. `conandata.yml` 用 **GitHub 官方 tag archive**（tag 名逐字核对：本例 `v2.2.7`）+ 固定 sha256；
   `source()` 用 `get(..., strip_root=True)`。
2. `test_package/tests/` ← 上游 `test/*.py` **逐字节副本**（含 `__init__.py`，pytest 以包方式导入）；
   `test_package/filecheck/` ← 上游 `test/filecheck/` 逐字节副本（含 `lit.cfg`）。
3. `test_package/snitch/` ← 上游 `snitch/`（wheel 里没有），并把它所在目录放进 `PYTHONPATH`；
   `test_package/programs/` ← 上游 `examples/` 的样例汇编，供消费者 E2E 使用。
4. `test()` 内两套都跑，各自落标记后聚合一条：

```text
HMBS_UPSTREAM_SUITE_PYTEST={"status":"passed","framework":"pytest","discovered":49,"passed":49,...}
HMBS_UPSTREAM_SUITE_LIT   ={"status":"passed","framework":"lit","discovered":11,"passed":11,...}
HMBS_UPSTREAM_TEST_RESULT ={"status":"passed","framework":"pytest+lit","discovered":60,"passed":60,...}
```

## 验证

```bash
$ conan create archives/r/riscemu/2.2.7 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 期望：49 + 11 全 pass，两个 suite 标记 + 一条聚合标记
$ grep HMBS_UPSTREAM_TEST_RESULT reports/conan-create.log
```

## 禁止做法

- ❌ 用 PyPI sdist 当 source 却在 `test_package` 里 `pytest tests/`（路径不存在 → 门禁失真）。
- ❌ 只跑 pytest 就宣称「已接入上游测试」（漏掉 lit 套件）。
- ❌ 为了「让 pytest 找到测试」把上游 `test/` 重命名/改造（副本必须逐字节等于上游）。

## 查重关键词

PyPI sdist 不含测试、单数 `test/`、pytest 与 lit 双套件、`refs/tags`、tag `v` 前缀、
sha256 固定、`strip_root`、`test_package/tests`、`xdsl_src`、snitch 未随 wheel 发布、
`file or directory not found`
