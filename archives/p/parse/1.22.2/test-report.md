# parse 1.22.2 测试报告（双口径台账）

## 统计口径

| 口径字段 | 数值 | 说明 |
|---|---|---|
| source_declared_total | 98 | 官方 tag 源码 pytest 采集的独立用例总数（`pytest --collect-only` 实测） |
| configured_executable_total | 98 | 当前 OHOS python3.12 配置全部实例化（无禁用/无互斥分支） |
| executed_passed_total | 97 | 实际运行并通过 |
| failed_total | 0 | 实际运行失败 |
| skipped_total | 1 | 版本条件 skip（见下） |
| uninstantiated_total | 0 | 无未实例化项 |

全量通过率：97/98 (99.0%)；当前配置可执行集合通过率 97/97 (100%)。

## 用例枚举与映射（源码声明 -> 执行）

| 测试入口 | 独立用例数 | 分类理由 | 是否实际运行 | 结果 |
|---|---|---|---|---|
| tests/test_parse.py | 51 | 用户测试源独立 test_ 函数 | ✅ | 50 通过 / 1 skip |
| tests/test_bugs.py | 12 | 用户测试源独立 test_ 函数 | ✅ | 全部通过 |
| tests/test_parsetype.py | 13 | 用户测试源独立 test_ 函数 | ✅ | 全部通过 |
| tests/test_pattern.py | 11 | 用户测试源独立 test_ 函数 | ✅ | 全部通过 |
| tests/test_result.py | 4 | 用户测试源独立 test_ 函数 | ✅ | 全部通过 |
| tests/test_search.py | 4 | 用户测试源独立 test_ 函数 | ✅ | 全部通过 |
| tests/test_findall.py | 3 | 用户测试源独立 test_ 函数 | ✅ | 全部通过 |
| tests/check_typing.py | 0 | mypy 类型检查脚本（文件头明确 "not to be run with pytest"），非 pytest 用例，不计入 | 不适用 | 不适用 |
| tests/requirements.txt | 0 | 测试依赖清单，非用例 | 不适用 | 不适用 |

## 唯一 skip 项

- `tests/test_parse.py:775-776 test_too_many_fields`（skipif 装饰器在 :775，函数在 :776）：skip 原因
  "Python 3.5 removed the limit of 100 named groups in a regular expression" —
  是**版本条件 skip**（python3.12 已移除该限制，用例本身验证旧限制的兼容行为）。
  非依赖缺失、非平台限制、非当前库缺陷。恢复条件：无（目标 python 3.12 下该
  限制已不存在，无需恢复）。

## 运行命令与证据

```bash
# cwd: <worktree>/.oh-tmp/parse-1.22.2（官方 sdist 解包目录）
export TMPDIR=<writable tmp> TMP=<writable tmp> TEMP=<writable tmp>
python3 -m pytest -q -o addopts="" -o cache_dir=<writable cache>
# 输出: 97 passed, 1 skipped in 0.14s
```

- 全部 98 例均在当前环境实际运行；pytest 默认采集即当前配置实例化集合，二者一致
  （configured == source declared），故无 uninstantiated 项。
- 测试通过 parse 已安装产物（`PYTHONPATH` 指向 conan 缓存 package 目录）运行。

## 鸿蒙专项测试

- 新增 `tests/ohos_test_parse.py`（1 个真实业务场景脚本，8 项断言）：
  配置行解析、日志行解析、ISO 日期转换、多行日志流 findall、自定义类型
  （with_pattern 语义化版本）、无匹配容错、format 反向对齐（round-trip）。
- 实际运行：`[PASS]` x8，EXIT 0（见 ohos 专项测试日志）。
- 与上游 pytest、test_package 消费者用例分别计数，不重复充数。