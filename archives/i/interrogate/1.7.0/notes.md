# interrogate 1.7.0 适配笔记（HarmonyOS PC / OHOS armv8）

## 一、软件定位与选型理由

`interrogate` 是测量 Python 代码库 **docstring 覆盖率** 的 CLI 工具（MIT，
Lynn Root），`interrogate --fail-under 80` 类用法在质量门槛场景常见。上游为
src 布局纯 Python 包（`src/interrogate/`），无 C 扩展、无 ELF 产物，不涉及
OHOS 签名要求。CLI 工具按仓内 pytest/9.1.1 的命令件范式打包：模块树 +
`bin/interrogate` 入口，双通道 PYTHONPATH/PATH 导出。

## 二、源码与校验

| 项 | 值 |
|---|---|
| 上游 | https://github.com/econchick/interrogate |
| 版本 | 1.7.0 |
| sdist | `interrogate-1.7.0.tar.gz` |
| URL | `https://files.pythonhosted.org/packages/8b/22/74f7fcc96280eea46cf2bcbfa1354ac31de0e60a4be6f7966f12cef20893/interrogate-1.7.0.tar.gz` |
| sha256 | `a320d6ec644dfd887cc58247a345054fc4d9f981100c45184470068f4b3719b0` |
| 许可 | MIT |

sha256 取自 PyPI JSON API，本机下载复算一致。vendored py 1.11.0 sdist
（`51c75c4126074b472f746a24399ad32f6053d1b34b68d2fa41e558e6f4a98719`）
同口径核验。

## 三、构建方式

`application` 包型 + 直接铺树（pytest/9.1.1 命令件范式）：

1. `source()`：解压官方 sdist（`strip_root=True`）。
2. `build()`：`src/interrogate/` 整树（含 `badge/` SVG 模板目录——
   `badge_gen` 经 `importlib.resources` 服务）→
   `staging/lib/python3.12/site-packages/interrogate/`；vendored `py/` 铺在
   同级；dist-info 含 `entry_points.txt`（`interrogate = interrogate.cli:main`，
   镜像上游 setup.py 的 console_scripts）。
3. `package()`：staging 整树 + LICENSE 进 `licenses/`。
4. `package_info()`：`buildenv_info`/`runenv_info` 双通道 PYTHONPATH + PATH；
   并 re-export 四个运行时依赖的导入路径（attrs/colorama 的 package_info
   不发布自身 site-packages，pytest/9.1.1 对 packaging/26.3 实测过同款
   "Skipped binaries" 失败模式，从这里补链）。

### 为什么不走 setuptools 构建

上游 `setup.py` 用 setuptools 动态读取版本/描述（`find_meta` 正则扫描
`src/interrogate/__init__.py`），但 `__version__ = "1.7.0"` 已烘焙在源码里，
无需构建期推断；铺树即得与 `pip install` 等价产物，构建依赖降为零。

### py 依赖的 vendor 决策（关键）

上游 `Requires-Dist: attrs, click>=7.1, colorama, py, tabulate`。W0 依赖
发布检查实测：

- attrs/26.1.0 ✅、click/8.4.2 ✅（满足 >=7.1）、colorama/0.4.6 ✅、
  tabulate/0.10.0 ✅（registry `conan download --only-recipe` 全过）
- **py：registry 零版本**（`conan list 'py/*' -r=ohpcd` → 0 recipes；
  1.8.2/1.9.0/1.10.0/1.11.0 逐一探测均报 "system acceleration policy not
  enabled"——该报错经伪造版本对照实验证实是**版本不存在**的报错形态，与
  packaging/99.99.99 完全一致；主仓 archives/p/py 目录为空；平台任务卡
  无 py 条目）

py 是 interrogate/utils.py 顶层硬导入（`from py import io as py_io`，
OutputFormatter 的 TerminalWriter）。缺件数 = 1，未超派工令的 2 件断链阈值，
且 py 已被上游 pytest 生态废弃（pytest/9.1.1 自带 py.py shim 正是为此），
单独立卡适配的长期价值低。故按 vendoring 处置：py 1.11.0 sdist 的 `py/`
包树（含其 `_vendored_packages/`，与 wheel 布局一致）铺进本包
site-packages，形成与 wheel 安装两包等价的自包含树。conandata.yml 的
`vendored_py` 段记录源与 sha256，可复核可追溯。

## 四、上游测试的真实执行

`build()` 中调用 `_run_upstream_tests()`：

1. pip `--target` 自举 `pytest==9.1.1` + `pytest-mock==3.16.0`（套件的
   `mocker` fixture 依赖；不能进 build_requirements，与 iniconfig/2.3.0
   同理避免循环）。
2. **tabulate 钉版 0.9.0 wheel**（URL+sha256 精确锁定）：上游 1.7.0 的
   expected-output fixtures 按 tabulate 0.9.x 列宽生成；0.10.0 每格加宽
   1 空格（两侧共 +2 列），导致 5 个 verbosity=2 fixture 对比漂移
   （实测：0.9.0 渲染与 fixture 逐字节一致；0.10.0 下 Detailed 表格差
   2 列）。工具本身在 0.10.0 下功能完好，registry 依赖保持 0.10.0，
   套件侧钉 0.9.0 保 fixture 对比，test_package 则用 registry 0.10.0
   驱动真实 CLI 验证功能。这是 pytest/9.1.1 `_SUITE_WHEELS` 的同款手法
   （把 index 的版本选择权收走，保证可复现）。
3. `PYTHONPATH = staged树:test-deps(含0.9.0):attrs包site:click包(平铺):colorama包site`，
   staged 树置前——测的是将要打包的那份。
4. `--basetemp` 避开 HMDFS/tmp 只读（同 pytest/9.1.1 `_suite_tmpdir` 顺序）。

实测结果：**228 passed / 13 skipped / 0 failed**（13 个 skip 全为上游
`IS_WINDOWS` 标记的 windows-only 用例，Linux/OHOS 上游语义即 skip）。
套件规模 241（7+10+8+9+11 个 `def test_` 加参数化展开为 241 项）。

## 五、test_package 消费者断言

`test_package/test_interrogate.py` 共 27 项断言：interrogate 与 vendored py
双来源校验（PYTHONNOUSERSITE=1 隔离）+ 四依赖逐个来源校验（attrs/click/
colorama/tabulate 从各自包文件夹导入）+ 版本/子模块完整性 + TerminalWriter
可用 + dist-info entry_points + badge 模板随包 + PATH 上 `bin/interrogate`
可执行（--version 报 1.7.0）+ fail-under 退出码契约（rc=0/rc=1）+
`-g` badge 生成真实 SVG。以 `env="conanrun"` 运行，消费方视角的
PYTHONPATH/PATH 即打包树。

## 六、运行期要求

- 消费方 Python 版本需与打包时的 `X.Y` 一致（铺在
  `lib/python3.12/site-packages`）。
- CLI 入口 `bin/interrogate` 为 `#!/usr/bin/env python3` shebang，PATH 上
  需有 python3（pytest/9.1.1 的 bin/pytest 同款约定）。
- 纯 Python 无动态库，不涉及 OHOS loader 的 DT_RUNPATH 限制。
