# sixer 1.6 HarmonyOS PC 适配记录

- 上游：`https://github.com/haypo/sixer`，标签 `1.6`。
- 源码：`source()` 使用 `tools.files.get()`，URL 为官方 `https://codeload.github.com/haypo/sixer/tar.gz/refs/tags/1.6`。该 URL 末段是标签名、没有 `.tar.gz` 后缀，因此显式传入 `filename="sixer-1.6.tar.gz"`，并 `strip_root=True`。SHA-256 为 `676d1303b467b376677e934940c8eee59d280fa444ab912ccc4e4873eed3340b`。2026-10-06 在本机下载该 URL，文件 25148 字节，SHA-256 与上述值一致；归档根目录为 `sixer-1.6/`，含 `sixer.py`、`tests.py`、`COPYING`。不使用仓库内二进制归档，也不使用第三方镜像或明文 `http://`。
- 形态：纯 Python 命令行应用，不含 C/C++ 构建步骤，也没有运行时三方依赖。
- L0p：`settings` 声明 `os`、`compiler`、`build_type`、`arch` 四项。`package_id()` 仍执行 `clear()`，纯 Python 包不按 ABI 重复；`validate()` 仍只接受 OHOS。
- 兼容补丁：将正则表达式中的普通字符串字面量改为原始字符串，避免 HarmonyOS PC Python 3.14 的 `SyntaxWarning` 令上游子进程测试失败；正则匹配字符不变。
- 安装：把模块放入版本无关的 `lib/python/site-packages`，避免包布局绑定构建机 Python 小版本，并根据上游 `console_scripts` 声明生成 `bin/sixer` 薄启动器。仅支持 HarmonyOS（OHOS）；目标环境使用系统 Python 3.14 运行时，不引入 Conan Python 依赖。目标环境未提供 `setuptools`，Python 3.12 起也不再内置 `distutils`，因此配方不引入安装期网络依赖。
- CI：2026-10-06 的 #72518（CI-037，16:52）与 #72519（CI-010，17:02）都失败在 `checkout-pr`。机器人归类为源码下载超时，原始日志是 `missing binary patch data` / `binary patch does not apply`（`archives/s/sixer/1.6/vendor/sixer-1.6.tar.gz`）以及 `patch: Unknown option 'fuzz=3'`。PR `.diff` 对这个归档只有 Git 的二进制差异占位、没有补丁字节，`git apply` 和 `patch` 都应用不了。本次从分支删除该归档及 `vendor/`，源码改回上述 codeload URL。
- 验证：本头提交前，跳板机 `amax@114.212.20.39` 可达，但 `currentUser@127.0.0.1:2200` 返回 `Connection refused`。因此没有在独立 `CONAN_HOME=~/work/psj/ch-sixer13550` 上重跑 `conan create`、上游 `tests.py` 或消费者 `test_sixer.py`。更早的离线归档配方曾在 `CONAN_HOME=~/work/psj/ch-sixer13550-vendor` 上得到 `conan create` 退出码 0、上游 44/44、消费者 4/4（7 条断言）；那是旧取源方式的结果，不作为本头 `get()` 的实跑计数。
- HarmonyOS 工具登记：软件级 `commands.json` 将 `sixer/1.6` 登记为工具。
- 知识边界：新增草稿讨论无效正则字符串转义产生的语法警告及其对严格 stderr 测试的影响；不替代 Python noarch 包目录布局或 `commands.json` 规范。
