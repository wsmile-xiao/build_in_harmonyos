# tccutil 1.5.1 适配笔记

## 编译环境
- 构建系统: custom（纯 Python 脚本工具，无编译过程）
- 编译日期: 2026-08-14
- 编译器: 无（纯 Python，settings 仅 os/arch）
- 状态: built（真机预检后由 HMBS 更新）

## 上游信息
- 官方仓库: https://github.com/jacobsalmela/tccutil（Homebrew 收录的 tccutil
  1.5.1 唯一官方来源）
- 发布归档: https://github.com/jacobsalmela/tccutil/archive/refs/tags/v1.5.1.tar.gz
- sha256: 37c0d87bf95ab750806c4807003b44f0dc9574ef08ff480ffbb982caa9d8c7c7
  （已下载并用 sha256sum 核对）
- 归档内容（5 项）: tccutil.py / README.md / LICENSE / .gitignore /
  .github/workflows/python-app.yml
- 许可证: GPL-2.0
- 工具定位: macOS 系统 TCC.db（辅助功能权限数据库）管理工具，单文件 Python
  脚本（约 393 行），无 C 扩展、无编译、无测试套件

## 编译步骤
纯 Python 应用，conanfile.py 的 build() 无编译，改为确定性自检（写入
conan create 日志可审计）：
1. `python3 -m py_compile tccutil.py` — 语法检查
2. 模块级自检：importlib 加载 tccutil.py，断言 `util_version == '1.5.1'`
   且 `display_version/display_help` 可调用（同时验证补丁的 import 容错生效）
3. CLI 自检：`python3 tccutil.py --version` 输出含版本号（真实执行
   main()/display_version() 路径）

package(): 将 tccutil.py 复制为 `bin/tccutil`（chmod 755），并再次
`python3 bin/tccutil --version` 包内自检。产物仅一个可执行脚本。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 无 `python` 命令，脚本 shebang `#!/usr/bin/env python` 失效 | 上游面向 macOS，默认 python | 补丁：shebang 改为 `#!/usr/bin/env python3` |
| 2 | 模块 import 即崩：`packaging.version.Version('')` 抛 InvalidVersion | 非 macOS 平台 `platform.mac_ver()[0]` 返回空字符串，原代码顶层直接 `osx_version = version(mac_ver()[0])` | 补丁：try/except 容错回退 `version('0.0.0')`，使全部 macOS 版本门槛分支不可达，--version/--help 等平台无关能力仍可用 |
| 3 | OHOS 精简环境可能未安装 `packaging` 第三方库 | 上游 import 第三方库 packaging | 补丁：try/except ImportError 提供最小版本比较回退类（仅 __ge__/__lt__，用于 macOS 版本门槛比较，非 macOS 分支不可达） |

## 源码修改
- `patches/0001-tccutil-py-ohos-compat.patch`（portability）：
  1. shebang `python` → `python3`
  2. `from packaging.version import Version as version` → try/except
     ImportError + 最小回退类
  3. `osx_version = version(mac_ver()[0])` → try/except 容错回退
     `version('0.0.0')`
- 均为实质性平台适配逻辑（非空壳 stub），改动最小化，未触碰 macOS 专属
  TCC.db 操作逻辑（该能力依赖 macOS 系统数据库，OHOS 上天然不可用，属工具
  固有平台限制，test_package/MANIFEST.yml 已说明）

## 依赖版本
- 运行时: python3（hmbs 注入 HMBS_PYTHON3 及 PATH 前置）
- 无 Conan requires 依赖

## 验证结果
```bash
# 真机预检（由 HMBS 在本轮结束后执行，环境与官方 CI 同源）：
# conan create ... 产出 HMBS_TEST_PACKAGE_RESULT（test_package 3 项消费者
# 断言：--version / --help / 模块 API）与 HMBS_UPSTREAM_TEST_RESULT
# （no_tests：上游无测试套件，discovered:0/executed:0）
```

## 真机失败修复记录（Round: fixing_verification）
- 失败：test_package 3 项断言仅过 2 项，
  `FAIL: module API: 'NoneType' object has no attribute 'loader'`，
  HMBS_TEST_PACKAGE_RESULT passed=false（discovered=3, passedCount=2）。
- 根因：test_tccutil.py 用例 3 用 `importlib.util.spec_from_file_location`
  加载包产物 `bin/tccutil`（**无 .py 后缀**）。CPython 对无法从扩展名
  推断 loader 的文件返回 `spec=None`（本地 Python 3.10 复现一致），随后
  `spec.loader` 即报 `'NoneType' object has no attribute 'loader'`。
  conanfile.py build() 自检加载的是源码树里的 `tccutil.py`（有 .py 后缀），
  所以构建阶段通过、test_package 阶段才暴露。
- 修复：显式 `importlib.machinery.SourceFileLoader("tccutil", cli)` +
  `spec_from_loader` + `loader.exec_module(mod)`，加载扩展名无关的脚本；
  `__name__ == "__main__"` 保护使 main() 不被执行。
- 本地验证：构造无扩展名脚本沙箱复现原错误（AttributeError 同真机），
  修复后 test_tccutil.py 3/3 通过，输出
  HMBS_TEST_PACKAGE_RESULT passed=true（discovered=3, passedCount=3）。
- readonly_tmp 诊断（`preflight.sh[229]: can't create temporary file
  /tmp/shtfuwe6.tmp: Read-only file system`）：HMOS /tmp 为 erofs 只读
  （知识库 E002）。本配方/test 脚本全程无任何 /tmp 写入（无 tempfile、
  无 mktemp、无 heredoc），该临时文件创建发生在 hmbs 预检脚本自身的
  mksh 临时文件逻辑中，非本库代码触发；按"最小适配"原则不改动配方，
  后续仍由 HMBS 注入的 TMPDIR/TMP/TEMP 兜底。

## 真机失败修复记录（Round: fixing_verification，上游测试证据）
- 失败：hmbs 判定「缺少 HMBS_UPSTREAM_TEST_RESULT 上游测试证据」，
  上游测试 发现/执行/通过 全 0。真机日志中标记为
  `HMBS_UPSTREAM_TEST_RESULT={{"status":"no_tests",...}}`（双大括号）。
- 根因：test_tccutil.py 输出上游 no_tests 标记的 print 语句沿用了
  `.format()` 风格的 `{{`/`}}` 大括号转义写法，但该 print 从未调用
  `.format()`，导致 `{{`/`}}` 原样输出为双大括号，整行不是合法 JSON，
  hmbs 机器证据解析失败。
- 修复：将该 print 改为单层大括号裸 JSON（`{"status":"no_tests",...}`），
  与经验「标记须裸 print 合法 JSON（status=no_tests, framework=none,
  discovered=0/executed=0，含 reason）」一致；HMBS_TEST_PACKAGE_RESULT
  的 print 因真正调用 `.format()`，其 `{{`/`}}` 转义保持不变。
- 本地验证：提取该 print 语句实际执行，`json.loads` 解析成功
  （status=no_tests, framework=none, discovered=0, executed=0），
  输出无双大括号。

## 注意事项
- **上游无测试套件**：v1.5.1 源码仅 5 个文件；CI workflow
  （.github/workflows/python-app.yml）只跑 flake8 lint，pytest 步骤整段被
  注释；无 tests/ 目录、无 test_*.py、无 Makefile check 目标。因此
  test_package/MANIFEST.yml 声明 `upstream_tests_exist: false` + 完整审计，
  test_package 输出 `no_tests` 上游标记，不伪造任何通过率。
- TCC.db 写入/读取功能为 macOS 系统能力，OHOS 上不可用（无该系统数据库），
  test_package 只验证平台无关的真实能力（CLI 版本/帮助、模块 API）。
- 真实机与命令属我方内部基建，不写进 PR 正文（正文统一写「在 HarmonyOS
  aarch64 环境实测」）。
