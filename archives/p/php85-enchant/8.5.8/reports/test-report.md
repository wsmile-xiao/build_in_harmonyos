# php85-enchant 8.5.8 真机测试报告

日期：2026-10-01。设备：HarmonyOS PC arm64，HongMeng Kernel 1.12.0。Conan 2.29.1（OHOS 适配版），profile `ohos-aarch64-device`，Clang 15.0.4。基准 `origin/main=255e5069639b3be244f4988c966a5120bd5608f2`。

## 来源及构建

官方 `https://www.php.net/distributions/php-8.5.8.tar.gz`，SHA256 `6ebc55e52af4396385e689f7af0f28944fbbf966843433b573e9dc1dc03df539`。只构建官方 ext/enchant，生产源码和 PHPT 不变。

`ohc-run.py conan-verify php85-enchant 8.5.8 --profile ohos-aarch64-device` 退出 0，G0/G1/G2/G3 通过。该工具未成功解析包 ID，G4/L2/L4/L5 给出了跳过信息，不能把这些输出声称为实际产物检查；模块已通过 conan create 的真实打包和消费者加载测试，产物与安全检查进一步由本地 CI 验证。

设备访问 php.net 曾连接重置。使用本任务私有 `core.sources:download_cache`，预填充 init-build 已下载并二次核验 SHA256 的同一官方发布包，单次命令配置，不改共享 Conan 配置、不改官方源码 URL。这属于下载缓存复用，不代表远程 CI 网络已通过。

## 上游 PHPT

完整清点：ext/enchant/tests/*.phpt 共 33 个。PHP 原始 run-tests.php 全部调度，没有删改任何测试或 SKIPIF。

| 状态 | 实测数 |
|---|---:|
| PASS | 9 |
| FAIL | 0 |
| SKIP | 24 |
| 总计 | 33 |

全量通过比例为 **9/33（27.27%）**；已执行且未跳过的用例为 **9/9（100%）**。24 个 SKIP 不计为通过。已发布 Enchant 2.8.2 关闭可选提供者，缺少自然语言字典/提供者的测试保留上游跳过行为，另有 Enchant 1 专属 API 前提。逐项原因保留于原始构建日志。

## 鸿蒙消费者测试

test_package/test.sh 调用 test_enchant.php，通过真实依赖 PHP 显式加载打包的 enchant.so。**12/12 断言通过**：模块加载、版本8.5.8、broker 对象、字典发现返回类型、空标签 ValueError、真实个人词表对象、词表内词接受、未知词拒绝、会话词记录及接受、移除后拒绝、词表文件路径。

不使用模拟后端。个人词表通过依赖 Enchant 的真实 API 处理。扩展损坏/缺失时第一条检查失败并退出 1，避免把无扩展环境当作成功。

## 当前限制

自然语言字典由 Enchant 提供者和相应字典数据提供；当前依赖包不自带这些资源，故不能声称英语等字典拼写能力已验证。个人词表和会话拼写功能有实测覆盖。平台 CI、AI 检视尚未执行；本报告未声明远程 CI 通过。

原始证据：本任务设备工作树 reports/conan-create.log（不提交），Windows 交接目录 tmp/php85-enchant-evidence/verify-4.log、results-4.log。最终本地 CI 结果另追加在此报告。

## 本地同源 CI

`CONAN_PROFILE=ohos-aarch64-device zsh ci/conan/build_and_test.sh archives/p/php85-enchant/8.5.8` 首轮退出 **0**。L0 全部通过、L1 消费者执行通过、L4 补丁危险函数扫描通过、L5 实际 lib/ 产物非空；L2 为纯扩展无 bin/ 的合理跳过。L1e 破坏性反向测试将模块 lib/ 移走后消费者失败，证明测试实质依赖被测模块。实际 conan create 打包路径及 revision 保留于原始日志，不把 G4 工具无法找到 ID 的提示当作产物验证。

原始同源 CI 日志：设备 tmp/php85-enchant-evidence/local-ci.log；Windows tmp/php85-enchant-evidence/local-ci-run.log。之后补齐文件头/软件级 manifest 格式和测试目录隔离，最终版本继续通过 finish 的强制 W3 验证后进入独立审计。

## 首轮 W3 与收尾

最终配方（含独立消费者构建目录）已通过 finish 内部 conan-verify 和 W3 本地同源 CI；.ci-result.json 由官方工具生成，exit_code=0，日志完整性哈希由工具保存。W3 再次运行真实消费者与破坏性反向验证。

finish 返回 1，失败步骤为 step5b（全仓既有 E219/E253/E305 知识字段不完整）。另有非阻断警告：泛化 G0 将完整 PHP 发布包作为对象，在根目录 configure 的 config.status 临时 awk 权限检查失败；本任务只构建 ext/enchant，真实干净构建由 Conan 完成并通过。没有将泛化 G0 声称为通过，也没有安装整套 PHP 到共享前缀。软件汇总生成器另报存量类型错误。未修改框架或其他归档。

已清理本任务 manifest 中将说明文字误写为知识引用的字段，现有 E273 使用记录保留在 notes.md，无新知识贡献。release tar 来自实际 Conan package，未制作或声称存在未构建的 debug 包。上述收尾警告不改变真实 W3 的通过结果。

## 审计修订后的最终验证

首轮 W4 指出 R6：直接改写生成 configure 不合规。最终配方通过 generate() 写入构建目录私有 ohos-tempdir.m4，覆写 AS_TMPDIR 宏；私有 phpize 生成 configure.ac 时将此宏置于上游模板前，由 Autoconf 正常生成 configure。配方只读检查生成结果，不直接修改生成文件；没有修改共享 Autoconf/PHP 工具、生产 C 源码或原版 PHPT。

硬编码 --build 已移除，依赖自带 config.guess 实测输出 aarch64-unknown-linux-ohos。消费者方法顺序建议一并修正。曾尝试私有 BASH_ENV 及 shell 包装器，中间 G2/W3 权限失败均为真实失败，未用于最终通过结论；最终实现不包含这两种方案。

修复后从阻断步骤继续调用官方 FinishPipeline.step3_verify_build、step35_local_ci 与后续收尾方法，不重复已确认对象不适用的完整 PHP 泛化 G0。最终 Conan 验证和 W3 都通过；.ci-result.json 由官方 finish 实现生成，非手工创建或修改。最终日志：设备 tmp/php85-enchant-evidence/finish-m4-final.log、conan-create-final.log、w3-local-ci-final.log；Windows 同名证据文件保存在 tmp/php85-enchant-evidence/。

最终代码实测：全部 33 个原版 PHPT 调度，9 PASS / 0 FAIL / 24 SKIP；消费者 12/12；本地 CI 的 L1e 移走 lib/ 后消费者失败，反向验证通过。9/33=27.27%，非跳过用例9/9=100%，SKIP不计PASS。依赖没有自然语言字典后端的限制保持不变。全仓知识字段/汇总的存量警告仍记录为警告，不宣称泛化 G0 通过或平台 CI 通过。
