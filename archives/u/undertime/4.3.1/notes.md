# undertime 4.3.1 适配笔记

## 编译环境
- 构建系统: python（setuptools + setuptools_scm，纯 Python 3，无原生编译）
- 编译日期: 2026-09-24
- 解释器: python3 3.12.9（本地）/ HNP python 3.12.8（CI worker）
- 状态: built

## 编译步骤

上游是纯 Python 3 命令行工具，`setup.cfg` 的 `[options] scripts` 直接安装 `undertime`
脚本，无编译阶段，只有打包阶段：

1. 私有 deps-build 目标：`pip install --target=<build>/deps-build setuptools wheel
   setuptools_scm pytest pytest-cov pytest-timeout`（PEP 517 后端 + 测试工具；
   本机解释器不自带 setuptools，后续 `--no-build-isolation` 安装要靠它）
2. 私有 deps-run 目标：`pip install --only-binary=:all: --target=<build>/deps-run
   pytz pyyaml termcolor tabulate tzlocal tzdata python-dateutil`
   （全部纯 Python，无 C 扩展依赖——原因见问题 #7）
3. 私有 prefix 安装本体：
   `SETUPTOOLS_SCM_PRETEND_VERSION=4.3.1 PYTHONPATH=<deps-build> pip install --no-deps
   --no-build-isolation --prefix=<build>/prefix <源码目录>`
4. 真实执行上游测试套件：`TZ=UTC python3 -m pytest test_undertime.py -v`（10/10 通过）
5. 打包：bin/ 下脚本改写 shebang 并注入 package 相对 site-packages 引导；
   dist-info（`--version` 走 importlib.metadata）与 vendored 运行时依赖一并复制

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pip install .` 版本解析失败 | `pyproject.toml` 用 setuptools_scm 从 git tag 取版本，GitLab 发布 tarball 不是 git checkout | 构建时注入 `SETUPTOOLS_SCM_PRETEND_VERSION=4.3.1` |
| 2 | 安装后的脚本无法执行 | 上游 shebang 为 `#!/usr/bin/python3`，本平台无该路径 | 打包时改写为 `#!/usr/bin/env python3` |
| 3 | 裸环境下 `undertime --version` 报 ImportError（pytz 等） | L2 冒烟测试不带 conan runenv；pip 依赖不是 conan 包，不会自动进入依赖链 | 运行时依赖 vendored 进包内 site-packages，并在脚本内注入 package 相对路径引导 |
| 4 | pip 安装被重定向/报 `--target` 与 `--prefix` 冲突 | 环境级 `PIP_TARGET`/`PIP_ONLY_BINARY`/`PIP_INDEX_URL` 覆盖了命令行参数 | 调用 pip 前剥离全部 `PIP_*` 环境变量，再显式传 `--index-url/--target/--prefix` |
| 5 | C 扩展依赖（ephem/pyyaml/regex）无本地编译需求 | 社区 PyPI 镜像已发布 cp312 `ohos_aarch64` wheel | `--only-binary=:all:` 直接解析 wheel，不触发源码构建 |
| 6 | 6 个上游用例报 `ZoneInfoNotFoundError: tzlocal() does not support non-zoneinfo timezones like UTC` | 本平台无 `/usr/share/zoneinfo`，stdlib `zoneinfo` 无数据库可读，`tzlocal.get_localzone()` 因此失败（`pytz` 自带数据，故 `--list-zones` 用例仍通过） | vendored 运行时依赖补入 `tzdata`（PyPI 版 zoneinfo 数据库，`zoneinfo` 自动回退使用）；这同时也是本平台工具可用的**功能必需项**，非仅测试需要 |
| 7 | **CI（#58278）上游 pytest 6/10 失败：dateparser 解析日期返回 None** | CI worker 用 HNP python 3.12.8（AppSpawn 沙箱），**无法 dlopen 用户空间 C 扩展 .so**（本地实证：对 `cp312-ohos_aarch64` wheel 中 .so 改名匹配 HNP 后缀后仍报 `Permission denied`；CI 日志中 coverage tracer 同报）；`dateparser` 硬依赖 `regex`（C 扩展）→ 不可用 → 6 个日期解析用例全挂。本地 python 3.12.9 能加载这些 .so，故本地 W3 曾 10/10 通过、掩盖了 CI 差异 | **不再 vendored dateparser/ephem 两个 C 扩展依赖**；新增源码补丁 `patches/0001-undertime-dateutil-fallback.patch`：`parse_date_dateparser` 在 `import dateparser` 失败时回退到上游已依赖的纯 Python `python-dateutil`，并 `astimezone(local_zone)` 对齐 dateparser 的 `TIMEZONE=local_zone` 语义。修复后上游测试在 HNP python（3.12.8）沙箱实证 **10/10 通过** |
| 8 | `moonphases` 伴随脚本无法在 CI 运行 | 它硬依赖 `ephem`（C 扩展），CI 沙箱同样无法 dlopen | 本包不发布 `moonphases`（方案 A：关闭可选特性；功能损失面 = 月相计算工具不出包，主工具 undertime 完整可用），README/PR 已说明 |

## 源码修改

`patches/0001-undertime-dateutil-fallback.patch`：
- `undertime` 的 `parse_date_dateparser()`：`import dateparser` 失败时回退
  `dateutil.parser.parse(date, fuzzy=False)`；naive 结果 `replace(tzinfo=local_zone)`，
  aware 结果 `astimezone(local_zone)`（对齐 dateparser `TIMEZONE=local_zone` 语义）。

## 依赖版本

vendored 运行时依赖（全部纯 Python，来自社区 PyPI 镜像
`https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple`）：

| 包 | 版本 | 类型 |
|----|------|------|
| pytz | 2026.4 | 纯 Python |
| pyyaml | 6.0.3 | 含 C 扩展但有纯 Python 回退（CI 下 `_yaml` 加载失败自动回退） |
| termcolor | 3.3.0 | 纯 Python |
| tabulate | 0.10.0 | 纯 Python |
| tzlocal | 5.4.4 | 纯 Python |
| tzdata | 2026.4 | 纯 Python（zoneinfo 数据库；本平台无系统 /usr/share/zoneinfo，功能性必需） |
| python-dateutil | 2.9.0.post0 | 纯 Python（日期解析回退，见问题 #7） |
| six | 1.17.0 | 纯 Python（dateutil 传递依赖） |

不 vendored 的上游依赖：
- `dateparser`（依赖 regex C 扩展，CI 沙箱不可 dlopen）→ 补丁回退到 python-dateutil
- `ephem`（C 扩展，CI 沙箱不可 dlopen）→ `moonphases` 不出包

## 验证结果

```bash
# 上游测试套件（conan build() 内真实执行；证据见 reports/w3-local-ci.log 与 conan create 日志）
TZ=UTC python3 -m pytest test_undertime.py -v
# => 10 passed（本地 python 3.12.9 与 CI 等价 HNP python 3.12.8 沙箱均实证通过）

# 消费者视角（test_package；证据见 reports/conan-create.log）
python3 test_undertime_pkg.py <pkg>/bin <pkg>/lib/python3.12/site-packages
# => ASSERTIONS: passed=11 failed=0 total=11
```

附加独立验证（L2 冒烟本地因无 cache 路径跳过，手工补做）：包内 `bin/undertime` 在
`env -i`（无 PYTHONPATH、无 conan runenv）下 `--version` → `4.3.1` rc=0；固定日期三时区
表格正常输出。

## 注意事项

- 上游 `install_requires` 里的 `importlib-metadata` 只在 Python < 3.8 生效，本平台
  Python 3.12 用标准库 `importlib.metadata`，无需安装。
- `dateparser`/`parsedatetime`/`arrow` 在上游是函数内延迟导入（用于解析自然语言日期），
  `dateparser` 已排除（regex C 扩展），后两者上游为可选的"额外"解析后端，未在
  `install_requires` 中，故不打包；日期解析由补丁回退到 python-dateutil 覆盖。
- `moonphases` 不出包的原因与损失面见问题 #8 与 README。
---

**编译结束**: 2026-09-24 19:58
**最终状态**: built
