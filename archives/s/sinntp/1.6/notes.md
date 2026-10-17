# sinntp 1.6 适配笔记

## 基本信息

- 上游：https://github.com/jwilk/sinntp（作者 Piotr Lewandowski、Jakub Wilk，GPL-2.0-only）
- 主页：https://jwilk.net/software/sinntp
- 版本：1.6（2016-12-19 发布）
- 源码包：https://github.com/jwilk/sinntp/releases/download/1.6/sinntp-1.6.tar.gz（20315 B，sha256 \`351acc6cdf408ba2ce23277a89a90d0a6657932445e6a9effd882446e31560ea\`，顶层目录 \`sinntp-1.6/\`，strip_root=True）
- 类型：纯 Python 命令行工具（package_type=application），标准库 only，无第三方运行时依赖
- 状态：built（本轮完成未提交工作树，待 HMBS 真机预检与 rule4 门禁）

## 源码结构（tarball 共 30 条目）

- 入口：\`sinntp\`（主程序，\`__version__ = \'1.6\'\`，import nntplib/argparse/mailbox + 本地 plugins/utils）
- 包装器：\`nntp-get\` / \`nntp-list\` / \`nntp-pull\` / \`nntp-push\`（均为 \`#!/bin/sh\nexec "\${0%/*}/sinntp" "\${0##*-}" "\$@"\` 一行委托）
- 模块：\`plugins.py\`（debug/mimify/strip_headers）、\`utils.py\`（split_host/xdg/join_lines）、\`tests.py\`（上游测试）
- 文档：\`doc/manpages/*.1\`、\`doc/changelog\`、\`doc/NEWS\`、\`doc/COPYING\`（本配方仅打包 licenses/COPYING）
- 无 Makefile / setup.py / configure：纯脚本安装，无需补丁

## 适配方案（路径 A：基础适配）

- \`source()\`：conandata 官方 GitHub release URL + sha256 获取源码。
- \`build()\`：先 compile() 校验 \`sinntp\` 主脚本语法与 1.6 版本声明，再真实执行上游测试 \`python3 tests.py -v\`（见下节），失败即抛异常中断。
- \`package()\`：\`sinntp\` + 4 个 \`nntp-*\` 脚本 + \`plugins.py\`/\`utils.py\`/\`tests.py\` 复制到 \`bin/\` 并 chmod 755（bin/ 内同时保留模块，保证脚本同目录 \`import utils\` 可用）；\`plugins.py\`/\`utils.py\` 另复制到 \`lib/python/site-packages\` 供消费者 \`import\`；\`doc/COPYING\` 复制到 \`licenses/\`。
- \`package_info()\`：\`bindirs=["bin"]\`，\`libdirs=[]\`，\`libs=[]\`，runenv 注入 PYTHONPATH + SINNTP_PACKAGE_ROOT。
- \`package_id()\`：\`self.info.clear()\`（纯 Python，无 ABI 区分）。
- \`validate()\`：仅允许 Linux / OHOS。
- 无 patches（patches: {}），无新增系统依赖。
- 包装器 shebang 为 \`#!/bin/sh\`：在无 \`/bin/sh\` 的系统上请用 \`sh nntp-get ...\` 显式调用；主入口推荐 \`python3 bin/sinntp --help\`。

## 上游测试账本

- 计数口径：python_def，统计 \`tests.py\` 内 \`def test_\*\` 定义数。
- 实测盘点：\`grep -c def test_ tests.py\` = 14，分布：
  - test_split_host 7 个：test_domain / test_domain_and_port / test_ipv4 / test_ipv4_and_port / test_ipv6 / test_ipv6_in_brackets / test_ipv6_and_port
  - test_xdg 4 个：test_XDG_DATA_HOME_unset / empty / relative / absolute
  - test_join_lines 3 个：test_empty / test_trailing_lf / test_no_trailing_lf
- \`upstream_test_total = 14\`，\`upstream_test_count_method = python_def\`，\`upstream_test_in_build = true\`，命令 \`python3 tests.py -v\`。
- 上游测试均为纯本地单测（地址解析/XDG 回退/行拼接），无需网络、无需 NNTP 服务器。
- 计数规则：discovered 取 \`Ran N tests\` 汇总行；passed/failed/skipped 逐行扫 \`... ok\` / \`... FAIL\` / \`... ERROR\` / \`... skipped\`（单一来源，无字符串数数回退与算术修补）；生成标记前自检 \`passed + failed == executed\`、\`executed + skipped <= discovered\`、\`executed <= discovered\`。
- 证伪说明：\`tests.py\` 经 \`unittest.main\` 真实执行断言；若解析逻辑被破坏（如 split_host 端口处理），对应 \`... FAIL\` 会使 build() 按 failed 抛异常中断，不存在静默跳过（XDG 用例均 условий assertEqual，非 plan 探测）。

## 消费者测试设计（test_package，10 项检查）

- \`test_sinntp.py\` 从消费者视角验证安装后载荷（断言失败即非零退出）：
  1. split_host/domain、2. split_host/domain+port、3. split_host/IPv4、4. split_host/IPv6+port（utils 真实调用）
  5. join_lines/empty、6. join_lines/trailing_lf（mbox 组帧真实调用）
  7. plugins.mimify 默认 Content-Type 注入、8. plugins.strip_headers 指定头删除（email.message 真实对象）
  9. 安装后 \`sinntp --version\` 退出 0 且含 1.6、10. \`sinntp --help\` 退出 0 且含 sinntp（入口脚本真实执行）
- \`test_package/conanfile.py\` 用 \`sys.executable test_sinntp.py\` 真实运行（can_run 为 False 时直接抛异常，不静默跳过），成功后输出 \`HMBS_TEST_PACKAGE_RESULT={discovered:10, passedCount:10}\`。
- 反空壳：脚本 import 并调用了 utils/plugins API，入口脚本经 subprocess 真实执行；L1e 破坏性验证（移除产物）会使 import/执行失败。

## 本轮验证（Windows 工作站，不做编译结论）

- 官方 tarball 已下载并校验 sha256（351acc6c…560ea，20315 B），文件清单 30 条目已核对。
- \`tests.py\` 方法数 14 已用正则盘点（7+4+3），与 MANIFEST 声明一致。
- \`python -m py_compile\` 思路已在配方 build() 内等价实现（compile() 语法校验）。
- 未在本机运行 conan（规范要求真机验证）；配方语法已做 Python 编译检查，conanfile/test 脚本缩进与 JSON/YAML 引号已核对。
- 待 HMBS 真机预检：conan create 全链路（含上游 14/14 与消费者 10/10）与 rule4 门禁，数字以真机日志为准。

## 已知限制

- \`nntp-*\` 包装器依赖 \`sh\`；OHOS 上建议经 profile 的 bash/sh 调用。
- 在线 NNTP 拉取/推送功能需真实服务器，本配方不做在线集成测试（上游亦无此类测试）。
- man 手册页未安装到 share/man（idl 工具链外最小交付；如评审要求可补）。
- Python 3.13+ 按 PEP 594 移除标准库 nntplib：配方在 source() 内对 sinntp 主脚本做兼容处理，保证离线入口可用，网络命令缺 nntplib 时抛明确 NNTPError。

---

**编写日期**: 2026-10-13
**最终状态**: built（待真机预检）
