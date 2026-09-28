# SKILL 适配反馈 — sectar 1.02

## 背景
- 软件 / 版本：sectar 1.02；构建日期：2026-09-26；原构建系统：Autotools 1.4；交付构建：Conan 直接调用 OHOS C 编译器。
- 上游：https://sourceforge.net/projects/star/files/sectar/1.02/sectar-1.02.tar.gz/download
- 适配路径：A（基础适配 + 2 个最小源码补丁）；依赖：无；状态：本地 conan-verify 通过、远端 CI 待创建 PR 后触发。

## 情况
| 阶段 | 结果 | 证据 |
|---|---|---|
| init-build / lang-preflight | C 主体通过 | 上游 6 个 C 源文件 |
| 手工编译 | 成功 | OHOS/aarch64 静态编译；qemu-aarch64 --version 退出 0 |
| conan-verify | 成功 | G2 conan create + test_package 真跑，输出 `sectar OHOS aarch64 consumer OK` |
| finish / W3 | W3 本地 CI 通过；finish 总退出 1 | G0 古董 configure 不兼容；全仓 SUMMARY 扫描 qpdf 既有 manifest 报 str/list 解析异常，未修改他人归档 |
| PR / CI | 未提交 / 未触发 | 创建前先完成 W4 和 rule12；远端结果待平台提供 |

### 失败与处理
- 上游 `configure` 报 `Invalid configuration ... machine ... not recognized` 和 `ltconfig: you must specify a host type if you use --no-verify`；由于只有 CLI，无 libtool 库，改为由 Conan OHOS profile 的 C 编译器直接编译源文件，不伪造三元组。
- 初次 conan-verify 报 `BadZipFile: File is not a zip file`：SourceForge `/download` 无扩展名使 Conan 误选 zip；按 `E483` 用经过 SHA256 核对的本地 `.tar.gz` 下载并解压，重跑通过。引擎误命中 `E540`（runner PATH），以真实 traceback 为准。
- 上游 33 字节原文 AES 加/解密后 `cmp: EOF on plain after byte 33`，上游 CBC 格式未存原文长度；用 32 字节对齐的 C 消费者输入测试真实加解密、交叉编译和运行，不把非整块限制写成修复。
- `finish` 内嵌 W3 通过但总退出 1：`G0` 重走无关的古董 `configure`，`gen_summary` 在全仓另一个软件的两个既有 manifest 上触发 `'str' object has no attribute 'append'`；属于非阻断辅助步骤，不能跨包修改以掩盖。

### 知识和测试
- 参考 `E483` 排查 Conan URL 后缀；`E595` 已记录 LP64 文件头，不再重复造条目。
- 新增 `knowledge/drafts/E596-draft-88CF.{kv,md}`：仅描述 CBC 不存明文长度的独立故障模式，`draft-review` 返回 create、最高相似度 0.07；留给主编审核 promote。
- 上游目录/注册清点 0/0；新增鸿蒙特有消费者用例 1/1：`test_package/consumer.c`，交付静态 OHOS CLI 经 qemu-aarch64 执行、生成 C 源后编译并运行消费者。没有把 skip 算作 pass。
- AI 检视与远端 CI 目前尚无结果、意见数未知；首次 PR 前已准备完整反馈，之后只有必须修的意见或 CI 红才推新 commit。

## 效率与问题
- 关键瓶颈：古董 Autotools 的 libtool 对真实 triplet 不兼容；Conan `get()` 误识别扩展名；`conan-init` 按 Autotools 自动生库模板，手工纠偏 CLI 模式。
- 前两次验证一败（下载格式）一过（完整消费者）；耗时在取源、调试 CLI 格式而非依赖解析。尚无远端 CI 重试。

## 建议
### SKILL 设计改进
- `scripts/ohc/conan_recipe.py` 的初稿生成应先检测 `bin_PROGRAMS` 且无 `lib_LTLIBRARIES`，建议用户核对是否选择 CLI application；否则 `conan-init` 将 CLI 误生成 library，影响 `PF8`。
### 模板改进
- `templates/conanfile-autotools.py.tmpl`（生成的 `archives/s/sectar/1.02/conanfile.py` 初稿前 35 行）默认为 MIT、库类型和 `get(self, **sources)`，建议许可和 URL 扩展名未核对时给显式警告而非看似可用的值。
### 自动化补全
- `scripts/ohc/conan_recipe.py` 生成 `conandata.yml` 时仅提供 sha256 占位，`notes.md` 留构建系统候选占位，初始反馈把上游写成未知、补丁和测试数写 0：建议从已下载 tarball 与填实的 manifest、test_package 测试结果采集，并将前置填充提示放在 G1。
### 知识图谱覆盖
- 引擎初次 G2 `BadZipFile` 对 `E540` 错命中，而现有 `E483` 覆盖精确根因；建议将 `BadZipFile` 在 `source()` 阶段优先定位 `E483`。`E596` 草稿记载 CBC 尾块明文长度缺失及完整消费者验证，主编合并后决定是否 promote，不修改正式 graph/index。

## 作者
- 姓名：nyaco3
- 邮箱：aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- PR：尚未创建；创建后不因填写 PR 号码而单独推送。
