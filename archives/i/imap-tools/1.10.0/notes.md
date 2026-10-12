# imap-tools 1.10.0 适配笔记

## 编译环境
- **类型**: 纯 Python noarch（无编译）
- **编译日期**: 2026-10-07
- **Python**: 3.12.9（OHOS 环境）
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built

## 编译步骤（conan create 全流程）

```bash
conan create archives/i/imap-tools/1.10.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 下载 PyPI sdist（`imap_tools-1.10.0.tar.gz`，sha256 `3d2bee8e…34557`），
`strip_root=True` 解压。**零外部依赖**（PyPI `requires_dist` 为空）——`requires()` 无声明，
路径 A 基础适配。

### 2. 打包（package()）
纯 Python noarch——`shutil.copytree` 拷贝源码根的 `imap_tools/` 模块（含 `py.typed`）
到 `lib/python3.12/site-packages/`；`env_info.PYTHONPATH` 暴露导入路径。
**顶层 layout**（包目录 `imap_tools/` 在源码根，非 `src/` layout）——直接拷贝根下模块目录，
与 python-dateutil 的 src layout 处理不同。

不走 pip/setuptools 构建（`egg_info` 加载 entry point 在 OHOS 上报错——
同 python-magic / rich / python-dotenv 既有教训）。

### 3. 上游测试（build() 集成——R51/R4 实测回填）
上游 `tests/` 共 **27 个 test 函数**（8 个测试文件）。官方 sdist 的 `MANIFEST.in`
仅 `include LICENSE / MANIFEST.in / README.rst`，**未打包 helper 模块
`tests/utils.py` 与 `tests/__init__.py`**——导致依赖该 helper 的 5 个文件
（test_connection / test_folders / test_idle / test_mailbox / test_message）
在 sdist 内**连收集都失败**（collection error）。

因此按文件白名单显式指定离线可收集子集：

```bash
PYTHONPATH=. python3 -m pytest tests/test_imap_utf7.py tests/test_query.py tests/test_utils.py -q --no-header
```

**实测结果：21 passed / 0 failed（100%）**

| 文件 | 用例数 | 结果 |
|------|--------|------|
| tests/test_imap_utf7.py | 3 | passed |
| tests/test_query.py | 6 | passed |
| tests/test_utils.py | 12 | passed |
| **合计** | **21** | **21 passed / 0 failed** |

**未运行的 6 个用例（如实披露，非通过率分母）**：
- test_connection（1）、test_folders（1）、test_idle（1）、test_mailbox（1）、
  test_message（2）——均为**真实 IMAP 账号连接用例**
- 已进一步取上游 GitHub tag `v1.10.0` 的**完整源码**（含 sdist 未打包的
  `tests/utils.py` 与 `tests/__init__.py`），确认这 6 例的硬性前提：
  `tests/utils.py` 通过 **`tests/credentials.ini`** 读取 4 个真实邮箱服务商账号
  （`TEST_MAILBOX_NAME_SET = YANDEX / ZIMBRA / MAIL_RU / YAHOO`，各需
  `host / email / password / path_separator / test_folder`），且
  `MailboxTestCase.setUp` 会连接**全部 4 个**账号；该凭据文件上游**刻意不随仓库
  发布**（仓库内无模板）。
- 为代填账号，本轮尝试自建本地 IMAP 服务端，**两条路径均不可行**（系统性堵塞）：
  ①**仓库自带归档 dovecot/2.4.4**（本平台唯一真实 IMAP 服务端）无法启动——
  其二进制编译前缀为 `/`，运行期 exec 硬编码 `//bin/doveconf`、`//bin/doveadm`，
  而 OHOS 的 `/bin` 是只读软链（→ `/system/bin`）无法补软链；且 `doveconf` 会把
  二进制配置写到**硬编码的 `/tmp`**（只读，`TMPDIR` 对其无效）。已用 LD_PRELOAD
  垫片重定向 exec 路径使其推进到配置解析（`doveconf -c <cfg> -n` 可成功输出有效
  配置），但 `/tmp` 侧仍无法写入，最终
  `doveconf: Fatal: Failed to write binary config file`；
  ②改用纯 Python 的 **pymap 0.36.7**（PyPI，含 dict/maildir 后端）作服务端，
  进程可起但**端口始终未监听**（`Connection refused`）。
- 结论：这 6 例在本环境**不可执行**，属环境侧系统性堵塞，非被测逻辑失败。

### 4. 沙箱适配
OHOS 沙箱 `/tmp` 只读 + 工作目录属主不匹配——pytest 的 `tmp_path` fixture 会报
`OSError`。build() 内将 `TMPDIR` 指向当前用户属主的可写目录
`/data/storage/el2/base/cache`（同 python-dotenv / rich 教训）。

## 验证结果
- **构建**: `imap-tools/1.10.0: Package created`（conan create EXIT=0）
- **上游测试**: 实测 **21/21 通过（100%）**——分母=离线可收集用例；
  剩余 6 个真机连接用例因**本环境无可用 IMAP 服务端**（dovecot 2.4.4 硬编码
  `//bin` + 只读 `/tmp` 无法启动、pymap 无法监听）且上游不提供测试凭据
  （`tests/credentials.ini`）而不可执行，如实披露（详见上节）
- **R34 消费者验证**: test_package 实测 6 项断言全过——模块 11 个文件齐全 +
  `import imap_tools` + 真实离线 API 调用（查询构建器 `AND/OR/NOT` +
  `A(header=H(...))`、`MailMessage.from_bytes` 解析真实 RFC822、
  `imap_utf7` 编解码往返、`__version__` 与公开类）

## 与 Linux 的差异
无差异——纯 Python（标准库 imaplib/email 封装），全平台行为一致。
