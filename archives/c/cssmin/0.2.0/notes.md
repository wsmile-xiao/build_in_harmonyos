# cssmin 0.2.0 适配笔记

## 编译环境

- **类型**：纯 Python noarch（无编译）
- **编译日期**：2026-09-12
- **Python**：3.12（OHOS 真机）/ 3.11（本地行为核验）
- **平台**：arm64-ohos（OpenHarmony PC）
- **状态**：built（待真机预检回填证据后由 HMBS 提交）

## 上游信息

- PyPI：https://pypi.org/project/cssmin/0.2.0/
- 源码：https://files.pythonhosted.org/packages/8e/d8/dc9da69bb186303f7ab41adef0a5b6d34da2fdba006827620877760241c3/cssmin-0.2.0.tar.gz
- sha256：e012f0cc8401efcf2620332339011564738ae32be8c84b2e43ce8beaec1067b6
- GitHub：https://github.com/zacharyvoase/cssmin（已归档，NO LONGER MAINTAINED）
- 许可：MIT（LICENSE 文件，PyPI 元信息标 UNKNOWN）
- 布局：setup.py（py_modules=['cssmin']，package_dir src，console_scripts cssmin=cssmin:main）+ src/cssmin.py 单模块

## 上游测试审计（no_tests）

- sdist 内容：MANIFEST.in、PKG-INFO、setup.cfg、setup.py、src/cssmin.py、src/cssmin.egg-info（dependency_links/entry_points/PKG-INFO/SOURCES/top_level），共 3.2 kB。
- 全树无 tests/ 或 test/ 目录；无 test_*.py；无 TEST/TEST_F；无 def test_；无 Makefile/ctest/pytest/tox 配置；setup.py 无 tests_require/test_suite。
- GitHub 文件列表：src、.gitignore、LICENSE、MANIFEST.in、README.md、setup.py，无测试入口。
- 结论：上游确无测试。test_package/MANIFEST.yml 已按规范写入 upstream_tests_exist: false 与非空 upstream_test_audit，真机输出 status:"no_tests"、discovered:0、executed:0 及具体 reason。

## 本地行为核验（非真机，仅用于编写正确断言）

- `cssmin('body { color: red; }')` -> `'body{color:red}'`
- `cssmin('/* comment */ body { margin: 0px; }')` -> `'body{margin:0}'`
- `cssmin('p { color: rgb(51, 102, 153); }')` -> `'p{color:#369}'`
- `cssmin('a { color: #AABBCC; }')` -> `'a{color:#ABC}'`
- `cssmin('p { margin: 0.6em; }')` -> `'p{margin:.6em}'`
- 反例：`cssmin('a{} b { color: blue; }')` -> `'a{}b{color:blue}'`（remove_empty_rules 定义后未被 cssmin() 调用，故不断言空规则删除）；`margin:0 0 0 0` 多维零在分号移除后不匹配，未压缩（属实记录，不美化）。

## 配方设计

- `conanfile.py`：settings 四项齐全；validate 限制 Linux/OHOS；source() 用 get(strip_root=True)；build() 做 py_compile 烟雾检查并明示无上游套件；package() 用 shutil.copyfile 将 src/cssmin.py 安装到 lib/<py_ver>/site-packages 并复制 LICENSE；package_info 置 cpp_info.libs=[] 并追加 env_info.PYTHONPATH。
- 未向 bin/ 安装 console script：按库类型适配（同 python-dotenv 先例），故无需软件级 commands.json。
- `test_package/test_cssmin.py`：6 项真实断言，每项校验非空与精确输出，第 6 项外加 main() CLI 管道验证；test_package/conanfile.py 输出 HMBS_TEST_PACKAGE_RESULT（discovered=6）与 HMBS_UPSTREAM_TEST_RESULT（no_tests/0）机器标记。
- 零依赖（仅标准库 re/optparse/sys/io），无需 W0 依赖发布检查项。

## 待真机回填

- conan create 全流程日志、test_package 6/6 证据、上游 no_tests 标记，均待 HMBS 真机预检轮次实测回填，不得本地猜测。
