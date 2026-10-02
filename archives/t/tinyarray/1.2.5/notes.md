# tinyarray 1.2.5 适配记录

## 上游与源码

- 上游：`https://gitlab.kwant-project.org/kwant/tinyarray`
- 固定版本：tag `v1.2.5`，commit `99c2fd8396de4f8a833d5b7a3124bb80452046d8`
- 官方 GitLab tag 归档 SHA-256：`445ac905745c462a8a939103c8fe5c4b527a735b3b053c7de168daa64fe38a3a`
- 构建：在目标 HarmonyOS CPython 上运行上游 `setup.py build_ext --inplace`，保留由 `EXT_SUFFIX` 决定的 CPython ABI 文件名。GitLab tag 归档不含 `.git`，上游 `version` 文件的 `__use_git__` 因而会退化成 setuptools 不接受的 `unknown`；配方在构建前将该哨兵固定为任务版本 `1.2.5`。Harmonybrew Python 未预装 setuptools，配方将 `setuptools==71.1.0` 隔离安装到 Conan build 目录；该版本仍提供上游 `setup.py` 导入的 `setuptools.command.test`。

## HarmonyOS/AArch64 边界修复

上游 `src/conversion.hh` 把 `long` 的最大值先转为 `double` 再比较。64 位 `long` 的最大值 `2^63-1` 转成 IEEE-754 `double` 会舍入为 `2^63`，因此 `2^63` 可能绕过比较；后续强转结果在 x86_64 与 AArch64 上不同。补丁改为在强转之前比较 `2^63` 与 `-2^63` 边界，并避免依赖架构相关的越界强转结果。该差异见 Debian bug #1146590。

Harmonybrew CPython 的 `LDSHARED` 还带有 `-lintl`，这是解释器本体的链接参数；HarmonyOS SDK 没有对应库，扩展链接因此失败。配方显式将 `LDSHARED`/`LDCXXSHARED` 设为目标 `clang++ -shared`，避免把解释器链接项泄漏到 CPython 扩展。

消费者测试覆盖扩展导入、`dot`/向量运算，以及 `float(2**63)` 与低于 `-2**63` 必须抛出 `OverflowError`、`float(-2**63)` 仍可转换、`2**63` 以下可表示值正常转换的边界；共 7 项断言。

## 测试说明

上游 `test_tinyarray.py` 含 18 个 pytest 测试函数，依赖 pytest 与 NumPy。本次 HarmonyOS 设备环境未安装这两项，因此上游套件未运行，按 0/18 记录，不把消费者测试计入上游通过率，也不将 pytest/NumPy 加入运行时依赖。消费者测试在 HarmonyOS/AArch64 上实跑 7/7 断言通过。

CI #64158 的 `conan create` 发现补丁 hunk 行数声明错误，Conan 停在补丁解析；修正 hunk 计数后，目标设备完整构建与消费者测试通过。CI #64161/#64163 随后定位到 HNP 沙箱拒绝从用户目录 `dlopen` 扩展（`Permission denied`），包括复制到 test_package 工作目录后。配方现于打包时使用 HNP `binary-sign-tool` 对 OHOS 扩展签名并设置可执行位；消费者测试仅在加载器错误明确为 `Permission denied`/`EACCES` 时采用 E212 静态回退，检查 ELF 魔数与 `.codesign` 段，其他导入错误仍失败。CI #64173 的 Conan `test_package`、L0、L1 均通过。

CI #64450 在 G0 知识库检查启动阶段因 CI worker 资源不足失败：日志显示创建 `grep` 与 `wc` 进程时返回 `resource temporarily unavailable`（exit 127）；未进入 Conan 构建或 test_package。此为 runner 资源错误，不是配方测试结果。已记录并将在新 head 上重新触发一次 CI。
