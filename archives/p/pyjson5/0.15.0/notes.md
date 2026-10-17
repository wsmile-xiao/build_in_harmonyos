# pyjson5 0.15.0 适配笔记

## 任务与结论概览
- 任务：pyjson5 0.15.0 R02 Python 类适配（R01 以 R47 env_unsupported 终态后由分析端
  以 python_class_task 重新下发）
- 结论：路径 A/知识库扩展判定见 reports/；上游测试 75/75 通过；conan create 通过；
  PR 已交付（见最终回报）

## 编译环境
- 构建系统: python（setuptools 打包，纯 Python 无编译，无构建族）
- 编译日期: 2026-09-21
- 解释器: python3.12（设备 3.12.9；配方依赖 conan python/3.12.9 保证 CI 复现）
- 状态: built（finish 后由工具更新）

## 适配要点
1. 官方 tag 实为 `v0.15.0`（非 0.15.0）。github.com 主站直连超时，经 GitHub 官方
   tarball 托管 codeload 获取，与官方 archive URL 重定向目标字节一致；
   sha256=ce5f13671a800f8e4a1123611e6af0603e410d2ffb93d4f79a9d7242f5e731b7。
2. 纯 Python：源码 30 文件（13 个 .py、0 个 C/C++ 源），pyproject.toml
   (setuptools.build_meta, packages=["json5"])，无 ext_modules，无补丁。
3. 配方形态（无构建/打包族，参考 conanfile-headeronly.py.tmpl 变体 B/C 与
   automysqlbackup application 包）：
   - package_type=application，settings 四项齐全，requires python/3.12.9
   - package(): copy json5/ → lib/python3.12/site-packages/json5/；
     save bin/pyjson5 console 等价包装（shebang env python3，相对路径前置
     site-packages 入 sys.path）；LICENSE → licenses/
   - package_id(): info.clear()（无编译 → 单一 package_id）
   - package_info(): cpp_info 清空 + bindirs=["bin"]；runenv_info 注入
     PYTHONPATH=site-packages、PATH=bin
   - R38：CLI 产物 bin/pyjson5 → 软件级 commands.json（type tool，
     ref pyjson5/0.15.0，commands: [pyjson5]）
4. 上游测试（75 个 unittest 用例 + 1 个 doctest 入口，官方 `python run tests`
   等价：`python3 -m doctest json5/lib.py` + `python3 -m unittest discover -p
   '*_test.py' -v`）：
   - 首轮 60/75 通过，15 例（tool_test.py 全部）失败：out-of-proc 子进程在
     临时 cwd 以 [sys.executable, -m, json5] 启动，上游依赖预安装环境(uv)，
     本机未安装 → ModuleNotFoundError: json5，rc=1
   - 恢复（运行时环境恢复规则，未修改任何上游测试）：注入精确
     PYTHONPATH=<源码根>（子进程继承）→ 重跑 75/75 OK + doctest 0
   - 双口径：source_declared_total=75（tests/ 三个文件 test_* 方法计数），
     configured_executable_total=75，executed_passed_total=75，失败 0，未运行 0
   - 台账与日志见 reports/ 与 ~/.oh-runner/logs/（upstream_tests_r02.log sha256
     f11778f5...）
5. HarmonyOS 专项测试：test_package/test_json5_ohos.py——在 OHOS 设备 python3.12
   上对已安装包执行 json5.loads/dump/dumps 公开 API + 中文注释 JSON5 配置解析 +
   HMDFS 真实文件 IO + round-trip 断言（TMPDIR 可写目录，规避 /tmp erofs）。
6. 消费者用例：reports/consumer/consumer_app.py——模拟配置中心消费方，仅用已安装
   公开 API（json5.loads/dumps）+ 运行时产物（bin/pyjson5 CLI 对真实配置文件做
   JSON5→JSON 转换），断言解析/派生/round-trip 结果，独立于上游与鸿蒙专项计数。
7. 环境坑位（沿用 SKILL §7）：
   - /tmp 为 erofs 只读：一切临时文件走 $TMPDIR=$HOME/tmp
   - HMDFS 账户 inode 耗尽（设备级 100%）：worktree 以 sparse 物化创建（R01），
     R02 直接复用；不影响任何 git 语义
   - HMDFS chmod 不生效（E046）：不依赖执行位/0700 断言

## 知识候选（详见 reports/knowledge_candidate_ledger.md 与七轴查重）
- 候选：纯 Python 无编译库在 OHOS PC 平台的 Conan 打包模式（site-packages
  copy + console wrapper + commands.json + runenv PYTHONPATH）
- 候选：纯 Python unittest 上游测试的运行时环境恢复（PYTHONPATH 注入）
---

**编译结束**: 2026-09-21 03:54
**最终状态**: built
