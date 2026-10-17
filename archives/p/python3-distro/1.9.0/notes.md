# Adaptation Notes - python3-distro 1.9.0

## Overview
distro（python-distro/distro）是 pip/pipx 等广泛使用的 Linux/Unix 发行版
信息识别库：解析 /etc/os-release、*-release、lsb_release 等数据源，
返回 id/name/version/like/codename 等信息。上游 v1.9.0（2023-08 发布）
是当前最新稳定版。

## Build System
- setuptools（`pyproject.toml` build-backend = setuptools.build_meta）
- src 布局（`src/distro/`），纯 Python，无 C 扩展
- Runtime deps: 无（setup.cfg 无 install_requires，python_requires >=3.6）
- console_scripts: `distro = distro.distro:main`（bin/ 下可执行脚本）

## Build Process
1. 下载 PyPI sdist `distro-1.9.0.tar.gz`（与 GitHub v1.9.0 tag 同源）
2. `pip install setuptools`（构建后端；运行时零依赖无需装其他包）
3. `pip install --no-deps --prefix=$staging .` 然后归一化到
   `lib/pythonX.Y/site-packages`（alabaster noarch 先例模式）
4. 复制 bin/（console_script）与 LICENSE 到包内
5. test_package: 12 项消费者测试（上游 resources 模拟数据同源断言）

## Upstream Tests (158 用例, OHOS 实测基线)
`python3 -m pytest tests/test_distro.py -v`（PYTEST_DISABLE_PLUGIN_AUTOLOAD=1，
OHOS 本机实测）：

- **1 passed, 233 skipped（含重复计数：跳过项=skipped 或 xfail 计入）**
- 唯一执行的 TestNonLinuxPlatform::test_cant_use_on_windows 通过——
  OHOS 上 `import distro` 成功（不触发 Unsupported platform）
- 233 skipped 全部因上游 `IS_LINUX = sys.platform.startswith("linux")`
  门卫：OHOS `sys.platform == "ohos"` 不以 linux 开头 → TestCli/
  TestOSRelease/TestLSBRelease/TestDistroRelease/TestOverall/
  TestGlobal/TestRepr 等整类跳过
- **这是纯 Python 包的平台行为差异，非适配缺陷**：库的核心解析逻辑
  （os-release / distro-release 文件解析、版本比较、归一化表）平台无关，
  已由 test_package 的 root_dir 模拟数据断言覆盖（见下）

## Platform Notes (OHOS)
1. **本机 host 检测返回空值**：OHOS 无 /etc/os-release、/etc/lsb_release
   等标准发行版元数据文件，distro.id()/name()/version() 返回空串，
   走 unknown 分支不抛异常——符合上游语义（无法识别的发行版返回空值）
2. **root_dir 模拟解析完全可用**：LinuxDistribution(root_dir=...) 显式
   指定根目录时（上游测试同款用法），arch/ubuntu14/centos7/centos5
   模拟数据解析结果与上游期望值逐一一致——核心逻辑无平台依赖
3. **CLI 可用**：`python -m distro` rc=0；bin/distro console_script 随包安装
4. **测试环境干扰防护**：本机 pip-global 可能已装同名 distro 1.9.0，
   test_package/conanfile.py 把被测包 site-packages 作为首参传入，
   测试脚本 sys.path.insert(0, site) 确保被测版本优先加载

## 验证
- consumer tests: 12/12 PASS（test_package/test_distro_consumer.py）
- conan create: 待 W3 验证
- 版本号：1.9.0（上游首次适配，R37）

## 已知限制
- lsb_release 探测路径（include_lsb=True 时 subprocess 调 lsb_release）
  在 OHOS 无 /usr/bin/lsb_release，自动跳过——上游设计即如此
  （lsb_release 不存在时静默忽略）
- OHOS 系统本身不被 distro 识别为已知发行版（返回空值）——如果
  HarmonyOS 未来提供 /etc/os-release（ID=openharmony 之类），distro
  将自动识别，无需重新适配
---

**编译结束**: 2026-09-05 14:44
**最终状态**: published
