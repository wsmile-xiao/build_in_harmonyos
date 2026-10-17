# dh-ros 0.15.0 适配笔记

## 构建环境

- 构建系统：Python setuptools + Perl 文件安装
- 目标语言：Python（含上游 Perl debhelper 插件）
- 源码：Debian native `dh-ros_0.15.0.tar.xz`

## 配方设计

`conanfile.py` 使用 pip 的 `--no-deps --no-build-isolation --target` 安装 Python 模块，避免引入无用途的 C/C++ 编译依赖。`rosbuilder` 使用稳定的包内 Python wrapper，Perl 插件安装到 `share/perl5/Debian/Debhelper/Buildsystem/`，并通过 `PERL5LIB` 暴露。

R26 说明：本包为纯 Python/Perl，不产出 `.so`，不存在系统同名库，故 R26（系统同名库静态链接）不适用。

## 依赖

- `perl/5.42.2.3` — 唯一的 Conan 依赖（Perl debhelper 插件运行环境）。
- `catkin_pkg` 1.1.0 — **运行时 Python 依赖，非 Conan 依赖**。`ohpcd` 制品仓没有可用的 `catkin-pkg/1.1.0` 配方（`conan download catkin-pkg/1.1.0 -r=ohpcd --only-recipe` 失败），因此按本仓库 `black/26.5.1` 的既有做法，在 `build()` 中用 pip 从社区源把 `catkin_pkg==1.1.0` 及其传递依赖（docutils、packaging、python-dateutil、pyparsing、six、setuptools）一并安装进包内 `lib/site-packages`，使安装后的 CLI 自包含。

## 测试

上游测试清单和实际执行边界如下：

- `tests/test_rosbuilder.py`：12 个参数化测试函数，收集到 134 个用例。
- `tests/test_topological_sort.py`：4 个用例。
- 上游 pytest 总计 138 个收集用例，执行结果为 `138 passed in 3.03s`。
- Debian autopkgtest 的 `run-cli` 和 `run-test-suite` 已在等价安装环境执行；`build-test-package` 需要 Debian `dpkg-buildpackage`、`debhelper`、`catkin` 和 `ament-cmake`，在 OHOS Conan worker 中未执行，原因已记录。
- `test_package/test_consumer.py` 额外验证安装后的 API、`rosbuilder --detect`、`--build-order` 和 `--help`。

## 验证结果

- 上游 pytest：`138 passed in 3.03s`。
- 消费者测试：导入 `catkin_pkg` 与 `dhros` API，并运行 `rosbuilder --detect`、`--build-order`、`--help`，全部通过。
- `conan-verify`：G1/G2/G3/G4 通过；该次运行的 L2/L4/L5 因无 cache 路径标记为跳过（报告 verdict 仍为 PASS），
  L2/L4/L5 的真实执行由 W3 本地 CI 完成（见下节）。
- Perl 插件已安装到 `share/perl5/Debian/Debhelper/Buildsystem/ros.pm`，并通过 `PERL5LIB` 暴露；完整 Perl 模块加载受 worker 缺少 Debian Debhelper 模块影响，未宣称该部分测试通过。

## 当前状态

配方、测试和归档元数据已完成，状态为 `built`（尚未上传制品仓，故 `commands.json` 的 `binary` 为 `false`）。

W3 本地 CI 模拟**已通过**（`build_and_test.sh archives/d/dh-ros/0.15.0` → RC=0），`.ci-result.json` 已落盘且 `exit_code=0`。逐项结果：

- `L0_RESULT=pass`（含 L0i 依赖检查通过：`conanfile.py` 依赖为 `perl/5.42.2.3`，制品仓可用）
- `L1_RESULT=pass`（`conan create` 成功，`test_package` 实际执行）
- `L1e` 破坏性负向验证通过（证明消费者测试真实依赖被测包，非空壳）
- `L2_RESULT=pass`（`rosbuilder --help OK`）
- `L4_RESULT=pass`（补丁无危险函数）
- `L5_RESULT=pass`（`bin/` 有产物）

## 依赖处理决策记录（catkin_pkg）

- `catkin_pkg` 是真实运行时依赖，不可删除：上游 `debian/control` 第 11 行 Build-Depends `python3-catkin-pkg <!nocheck>`，源码 `dhros/common.py:8` 为 `from catkin_pkg.package import Package, parse_package`，`setup.cfg` install_requires 亦声明 `catkin_pkg`。
- `ohpcd` 制品仓无该版本配方：`conan download catkin-pkg/1.1.0 -r=ohpcd --only-recipe` → `ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]`；
  revision 形式 `conan list "catkin-pkg/1.1.0#*" -r=ohpcd` → `not found`（与 `download` 结论一致）；同期 `perl/5.42.2.3` 正常可下载，排除通道全局故障。
  ⚠️ 口径提醒（R35）：纯通配 `conan list 'catkin-pkg/*'` 会返回 `Found 1` 假阳性，不得作为"已发布"证据；须以 `conan download` 实测为准。
- 决策：不做"捎带适配依赖"，改为包内 pip 捆绑（本仓库纯 Python 配方的主流做法，`black/26.5.1` 等 38/40 个配方不声明 Python 模块依赖）。
  社区 pip 源 `https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple` 提供 `catkin_pkg` 1.1.0 及全部传递依赖。

## 包装布局

- Python 模块：`lib/site-packages/`（含 `dhros`、`catkin_pkg` 及依赖）
- 可执行入口：`bin/rosbuilder`（包内自定位 wrapper，注入 `lib/site-packages` 到 `sys.path`）
- Perl 插件：`share/perl5/Debian/Debhelper/Buildsystem/ros.pm`
- 手册页：`share/man/man1/rosbuilder.1`
- 许可：`licenses/LICENSE`

> ⚠️ PR 正文：按 `templates/积分赛事PR模板.md` 生成，`submit` 读取 `reports/pr-body.md`（该目录被 `.gitignore` 忽略，不进入 PR 提交内容，仅作为 PR 描述来源）。
> 上游用例 138、消费者用例 1（8 条断言）的统计口径与 `test-report.md`、`test_package/MANIFEST.yml` 一致。
---

**编译结束**: 2026-09-23 12:45
**最终状态**: built
