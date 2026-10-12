# imap-tools

## 软件描述
imap-tools 是基于标准库 `imaplib`/`email` 封装的高层 IMAP 邮件客户端库，提供邮件读取、查询构建、文件夹管理与 IDLE 等能力。

## 功能概述
- **邮件操作**：`MailBox.fetch` / `uids` / `numbers` 拉取邮件与解析属性
- **查询构建器**：`AND` / `OR` / `NOT` / `H` / `U` 组合搜索条件
- **文件夹管理**：`mailbox.folder` 的 list / set / get / create / rename / delete / status
- **IDLE**：`mailbox.idle` 的 start / poll / stop / wait
- **消息解析**：`MailMessage` 的 text / html / attachments / headers / flags 等属性
- **工具函数**：`imap_utf7` 编解码、`utils` 的日期与地址解析

## OHOS 适配

### 构建方式
- **纯 Python noarch**：无编译——`package()` 用 `shutil.copytree` 拷贝 `imap_tools/` 模块（含 `py.typed`）到 `lib/python3.12/site-packages`
- 绕过 pip/setuptools 构建（`egg_info` 加载 entry point 报错实测——同 python-magic/rich/python-dotenv）
- `env_info.PYTHONPATH` 暴露导入路径给消费者

### 关键攻坚点
1. **零外部依赖**：PyPI `requires_dist` 为空，纯标准库实现——无需任何前置包（路径 A 基础适配）
2. **上游测试实测**：上游 `tests/` 共 27 个 test 函数——离线可收集 21 个（test_imap_utf7 3 + test_query 6 + test_utils 12），实测 21 passed / 0 failed；剩余 6 个为真实 IMAP 账号连接用例
3. **真机用例不可执行的客观原因**：①无 IMAP 测试账号（上游 `tests/utils.py` 依赖 MAIL_RU/YAHOO 等账号配置）；②官方 sdist 的 `MANIFEST.in` 只 `include LICENSE/MANIFEST.in/README.rst`，未打包 helper 模块 `tests/utils.py` 与 `tests/__init__.py`，这 5 个文件在 sdist 内连收集都会失败——按文件白名单显式指定可收集子集，避免 collection error 淹没真实通过率
4. **顶层 layout**：包目录 `imap_tools/` 位于源码根（非 `src/` layout），直接拷贝

### 与 Linux 的差异
- 无差异——纯 Python，全平台行为一致

## 依赖关系
无外部依赖（纯 Python 标准库）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.10.0 | built | 2026-10-07 | 纯 Python noarch 适配；离线单测 21/21 通过 |

## 参考资料
- 上游仓库: https://github.com/ikvk/imap_tools
- PyPI: https://pypi.org/project/imap-tools/
