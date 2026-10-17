# ubelt 1.4.0 适配笔记

## 环境
- 目标平台: HarmonyOS PC (OHOS 6.0, aarch64)
- 解释器: CPython 3.12.9（`sys.platform == 'ohos'`）
- 构建系统: python（PEP 517 / setuptools，`pyproject.toml` + `setup.py`）
- 包形态: `package_type = "python-require"`（纯 Python，无编译）
- 日期: 2026-10-04
- 状态: built

## 源码核验
- 上游: https://github.com/Erotemic/ubelt （tag `v1.4.0` = `ffd95200fa5a`）
- sdist: `ubelt-1.4.0.tar.gz`
  - sha256: `84e146c1c3ba13a2425eea5d5748bf33ab3f9dbe7ce237eb11e130116ba17441`（与 PyPI digest 一致）
  - size: 296335 bytes

## 语言与形态判定（R47）
- 源码树 59 个 `.py`、0 个 C/C++ 文件；wheel tag `py3-none-any`
- `lang-preflight`（`--lang python`）= task=python / detected=python → 匹配
- 强制第三方依赖 = 0：`setup.py` 的 `install_requires` 取自空的
  `requirements/runtime.txt`（0 字节）；`PKG-INFO` / wheel `METADATA` 的
  非 extra `Requires-Dist` 计数 = 0；所有三方包仅挂 extras

## 适配步骤
```bash
# 1. 依赖可消费性（W0/R36）：本库零强制依赖，无需消费其他包
# 2. init-build（源码已在 .dep-analysis 取证，sha256 复核一致）
python3 scripts/ohc-run.py init-build ubelt 1.4.0 --url=<pypi-sdist>
# 3. conan-init（模板为 autotools 形态，改写为 python-require）
python3 scripts/ohc-run.py conan-init ubelt 1.4.0
# 4. test_package 改写为 python 形态（conanfile.py + test_ubelt.py + test_ohos_ubelt.py）
# 5. 验证
python3 scripts/ohc-run.py conan-verify ubelt 1.4.0
python3 scripts/ohc-run.py finish ubelt 1.4.0 built
```

## 上游测试（真机实测，2026-10-04）
- 命令: `python3 -m pytest -v -p no:doctest --xdoctest --xdoctest-style=google ubelt tests`
- 入口: `tests/` 25 个 `test_*.py`（244 个 `def test_`）+ 包内 xdoctest doctest
- 结果: **548 passed / 17 failed / 43 skipped**（合计 608）
- 日志: `ubelt-1.4.0-evidence/upstream_pytest.log`
- 17 项失败全部为环境限制（非 ubelt 缺陷）：
  | 类别 | 数量 | 根因 |
  |------|------|------|
  | `ub.cmd`/subprocess 裸命令名 | 15 | 本平台 `posix_spawnp` 不做 PATH 查找——`echo`/`ls`/`sha1sum` 传裸名必 `ENOENT`，绝对路径正常（`/usr/bin/echo` rc=0）；涉 `tests/test_cmd.py`(8) + `ubelt/util_cmd.py` doctest(6) + `ubelt/util_hash.py::hash_file:2`(1) |
  | passwd/home 解析 | 2 | 本平台无该 uid 的 passwd 记录，`pwd.getpwnam('100')` KeyError、`getpass.getuser()=='100'`；涉 `ubelt/util_path.py::userhome:0` + `tests/test_path.py::test_pathlib_compatability` |

## 源码修改
无。ubelt 为纯 Python（顶层 import 仅 CPython 标准库，三方 import 全部惰性且带
`try/except`）；`ubelt/util_platform.py` 的平台分派按
`POSIX = 'posix' in sys.builtin_module_names` 判定，OHOS 下取 POSIX 分支并遵循
运行时注入的 `XDG_CACHE_HOME`/`XDG_DATA_HOME`（应用沙箱 `/data/storage/el2/...`），
不会落入 `raise NotImplementedError('Unknown Platform ...')`。故无需补丁。

## 鸿蒙特有测试（≥1）
`test_package/test_ohos_ubelt.py`：
1. `sys.platform == 'ohos'`（平台标识）
2. `ubelt.util_platform.POSIX is True`，`platform_cache_dir()/platform_data_dir()`
   返回绝对路径（不抛 NotImplementedError）
3. `ub.Path.appdir()` 落在 `XDG_CACHE_HOME`（OHOS 沙箱）之内
4. 沙箱目录可真实创建/读写

## 交付物
- `archives/u/ubelt/1.4.0/{conanfile.py,conandata.yml,test_package/,manifest.yaml,notes.md}`
- 无 `commands.json`（R38：纯库，无 bin 载荷、无 console_scripts）

## 注意事项
- 无 patches；`patches/` 目录不存在。
- 可选依赖（numpy/xxhash/Pygments/python-dateutil/packaging 等）属 extras，
  默认 `pip install ubelt` 不拉取，制品不含。
---

**编译结束**: 2026-10-04 13:17
**最终状态**: built
