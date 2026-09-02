# ruamel-yaml 0.19.1 HarmonyOS PC adaptation notes

## Current Status

- Package version: 0.19.1
- Upstream package: ruamel.yaml 0.19.1 (PyPI sdist, git tag 0.19.1 = b6b5921)
- Source: https://files.pythonhosted.org/.../ruamel_yaml-0.19.1.tar.gz
- Build system: Python（零编译，源码直装）
- Local status: Conan recipe (f69c322650, 2026-08-24) 已发布制品仓 ohpcd；
  本次补全软件级 manifest / README / notes / 鸿蒙特有测试 + 积分赛 PR

## W0 Dependency Check

- Required upstream dependencies: **无**（sdist PKG-INFO Requires-Dist 核验：
  `ruamel.yaml.clib` / `ruamel.yaml.clibz` 仅 `extra=oldlibyaml/libyaml`
  可选；jinja2/docs 亦 extra）
- 运行时：纯 Python（`__with_libyaml__ = False` 实测）

## Source Verification（sdist vs git tag）

- sdist 36 个 .py 文件与 git tag 0.19.1（b6b5921 "Added tag 0.19.1 for
  changeset 6846cf136e77"）**逐一比对 identical**（README.md 除外——
  sdist 生成物）
- sdist 额外文件：PKG-INFO / pyproject.toml / setup.cfg / egg-info（打包物）

## Build

- `build()`: copytree 源码 → `/data/storage/el2/base/cache/ruamel-yaml-stage`
  （OHOS /tmp 只读，用源外目录）；同时从 GitHub 镜像下载 master 源码树
  真实执行上游 `_test/` pytest（管理员规则 4：上游测试必须真实执行回填）
- `package()`: 平铺复制 .py/.txt → `lib/python3.12/site-packages/ruamel/yaml/`
  + 空 `ruamel/__init__.py`（namespace package，pip 实测布局）

## Upstream Test Results（真实实测，HarmonyOS PC aarch64）

入口：`pytest _test/test_*.py`（tox.ini 官方入口，38 个顶层测试文件）

```
472 collected: 442 passed / 4 failed / 4 skipped / 22 xfailed  (93.6%)
```

失败 4 个（如实分类，均为平台/运行时环境差异，非适配缺陷）：

| 用例 | 根因 |
|------|------|
| test_cyaml::test_load_cyaml | clib 可选 extra 未装，`__with_libyaml__=False`（设计内） |
| test_cyaml::test_load_cyaml_1_2 | 同上 |
| test_cyaml::test_dump_cyaml_1_2 | 同上 |
| test_deprecation::TestYamlTyp::test_full_rt | HarmonyOS 包装层 `_harmonyos_compat` 替换 `os.system`，dump 出的 python/name tag 为 `_harmonyos_compat._wrapped_os_system`，`'posix.system' in tag` 断言不成立（平台行为差异） |

跳过 4 个：Py3 下旧 API 用例 2 个（`ok on Py3`）、
`ruamel.yaml not available`（独立包名导入检查）1 个、
空参数集 1 个。xfail 22 个为上游标注的已知限制。

## HarmonyOS-Specific Tests（新增，test_package/）

- `test_ohos_compat.py`（4 用例）：
  1. 平台导入 + 版本断言（HarmonyOS 上 namespace 包可 import）
  2. 注释保留 roundtrip（roundtrip 模式核心特性——注释往返不丢失）
  3. Unicode + CRLF（中文标量 + \r\n 换行 dump/load 往返一致）
  4. YAMLFile 真文件 IO（tmp 文件读写 + 注释保留）

## Knowledge

1. PyPI sdist 不含 `_test/`（tar tzf 全量核验 0 个测试文件）——上游测试从
   git 仓库获取；sdist 与 tag 源码比对一致，测试覆盖等效
2. HarmonyOS `os.system` 包装层 `_harmonyos_compat`——依赖其类型名的
   上游测试按平台行为差异分类
