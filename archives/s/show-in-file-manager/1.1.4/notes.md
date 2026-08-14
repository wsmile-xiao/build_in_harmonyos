# show-in-file-manager 1.1.4 适配笔记

## 三重身份

| 身份 | 名称 | 说明 |
|------|------|------|
| 平台 | show-in-file-manager 1.1.4 | 任务平台库名/版本（Issue #2082） |
| 上游 | damonlynch/showinfilemanager v1.1.4 | GitHub 官方仓库；PyPI 包名同为 show-in-file-manager |
| 归档 | conan show-in-file-manager/1.1.4 | archives/s/show-in-file-manager/1.1.4/ |

上游仓库名（showinfilemanager）与包名（show-in-file-manager）为同一项目的
GitHub 仓库名与 PyPI 包名差异，版本号一致（1.1.4 = v1.1.4），无需映射解释。

## 包来源

- 上游: https://github.com/damonlynch/showinfilemanager（tag v1.1.4）
- 源码 URL: https://github.com/damonlynch/showinfilemanager/archive/refs/tags/v1.1.4.tar.gz
- SHA256: a2990d8145206d032cb8e45c546fe5732d8a240f436f6f53d81d62d4c09e3159（实测核对）
- 许可证: MIT（LICENSE 文件，Copyright (c) 2021 Damon Lynch）
- 语言/构建: 纯 Python 3.6+，setuptools（pyproject.toml + setup.cfg + setup.py）

> 选择 GitHub tag tarball 而非 PyPI sdist 的原因：sdist 的 MANIFEST.in
> `exclude rundoctest.py` 排除了上游唯一自动化测试入口（src/rundoctest.py）
> 与 src/cli.py；tag tarball 为完整仓库，保证测试入口可用。两个来源的
> src/showinfm 内容完全一致（diff -rq 无差异）。

## 产物与消费方式

- Python 模块: `showinfm`（含 system 子包）→ 安装至 lib/python3.12/site-packages/showinfm/
- 命令行工具: `showinfilemanager`（console script 入口 showinfm.showinfm:main）→ bin/showinfilemanager
- 许可证: LICENSE
- 消费方式: `from showinfm import show_in_file_manager, valid_file_manager,
  user_file_manager, stock_file_manager`；或直接运行 `showinfilemanager file1.txt`
- package_info: runenv PYTHONPATH 注入 site-packages，bindirs=bin，无 C libs

运行时依赖: python3 解释器；`packaging`（linux.py 顶部无条件
`import packaging.version`）；`pyxdg` 为可选导入（try/except ImportError）；
`pywin32` 仅 Windows（本归档不涉及）。

## 平台适配补丁

1. `0001-system-init-harmonyos.patch`
   - 文件: src/showinfm/system/__init__.py
   - 原因: 上游仅识别 Windows/Linux/Darwin，HarmonyOS 上
     `platform.system()` 返回 "HarmonyOS"（实测），模块导入直接
     `raise NotImplementedError`。
   - 修改: `elif system in ("Linux", "HarmonyOS")`，按 Linux 平台处理。

2. `0002-linux-proc-version.patch`
   - 文件: src/showinfm/system/linux.py
   - 原因: 模块导入时执行 `detect_wsl()`，`open("/proc/version")` 在
     HarmonyOS 上 Permission denied（实测），导入崩溃。
   - 修改: `wsl_version()`/`detect_wsl()` 捕获 OSError 返回 None/False。

两处均为平台启动适配，未改变任何上游测试断言、数据、用例选择、skip 条件
或预期结果。

## 编译环境

- 构建系统: setuptools / PEP 517（pyproject.toml，build-backend=setuptools.build_meta）
- 编译日期: 2026-08-12
- 编译器: 无（纯 Python，无 C 扩展，settings 仅 os/arch）
- Python: 3.12.9（宿主）；目标包布局 lib/python3.12/site-packages
- 状态: built

## 编译步骤

```bash
# 1. PEP 517 wheel 构建验证（产物平台无关 py3-none-any；
#    不使用 --no-build-isolation：CI Worker 未预装 setuptools.build_meta，
#    标准隔离构建按 pyproject.toml [build-system] 准备后端）
python3 -m pip wheel --no-deps -w dist .

# 2. 模块导入自检（打补丁后，HarmonyOS 平台）
PYTHONPATH=src python3 -c "import showinfm; print(showinfm.system.current_platform)"

# 3. package() 内安装模块树 + 生成 bin/showinfilemanager + 包内自检
```

## 上游测试情况

上游唯一自动化测试入口: `src/rundoctest.py`（doctest 运行
`wsl_transform_path_uri` 的 docstring 示例）。sdist 经 MANIFEST.in 排除了它，
tag tarball 中包含。

实测（鸿蒙 PC 真机原生执行打补丁后的源码树）:

| 指标 | 数值 |
|------|------|
| doctest 用例总数（wsl_transform_path_uri） | 129 |
| passed | 52 |
| WSL/Linux 宿主环境专属不可执行（unrunnable） | 77 |
| errors / timeout | 0 / 0 |

上游真实通过率：**52/129（40.31%）**。77 项为 WSL/Linux 宿主环境专属
不可执行（unrunnable），**不属于 passed，也不属于上游条件性 skipped**
（上游没有 skip 条件）。77 项不可执行的原因均为上游 doctest 期望值依赖
WSL/Linux 宿主环境事实，本真机（HarmonyOS，非 WSL，is_wsl=False）无法构造：
`wslpath` 命令、`/mnt/c` Windows 盘挂载、`\\wsl.localhost` 或 `wsl$` 宿主 UNC、
`/etc/fstab`、`/home` 用户目录布局、特定 UID/passwd 数据库、Windows 路径转换
和文件存在性（例如 `r.win_path if r.exists else ...` 分支、
`file://.../.../home/...` 期望值、`pwd.getpwuid(os.getuid())`）。
逐例证据表见 evidence 分析（示例位置、依赖条件、原生结果、功能影响）。

这些测试集中在 `wsl_transform_path_uri`；该函数仅在 `showinfm.py` 的
`if is_wsl:` 分支被调用（is_wsl=False 时完全不经过），鸿蒙普通运行流程
不会进入 WSL 分支，不影响普通 show-in-file-manager 功能（import、API、CLI、
URI 工具由 test_package 验证）。

诊断驱动（platform 映射 + 临时 wslpath wrapper + 临时 HOME/文件树）曾得到
81 passed / 48 failed，**该结果仅用于根因分析，不代表鸿蒙真机通过率**，
不写入 PR 通过率。

未修改任何上游测试文件、断言、数据、用例选择、skip 条件或预期结果。



`rundoctest.py` 本身用 `doctest.run_docstring_examples` 运行且不设退出码
（退出码恒为 0），故以 doctest runner 的 attempted/failed 统计为准。

## 验证结果

```bash
# conan create（含 build 内 PEP517 wheel 构建 + import 自检 + package 自检 + test_package）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify show-in-file-manager 1.1.4
# → 通过（详见 conan-verify 输出与 conan create 日志）

# 产物结构（package 内）
#   bin/showinfilemanager
#   lib/python3.12/site-packages/showinfm/（含 system/ 子包）
#   LICENSE
```

## 补丁

2 个平台适配补丁（见上），均为 unified diff，`patch --dry-run -p1` 可复现。
---

**编译结束**: 2026-08-14 09:39
**最终状态**: built
