# preseq

preseq 用测序数据的抽样曲线估计文库复杂度和基因组覆盖度。此适配基于上游 3.2.0 正式发布包，启用 HTSlib 以支持 BAM 输入和 `to-mr` 工具。

## HarmonyOS PC 适配

- 使用带预生成 `configure` 的上游 release asset；GitHub 自动生成的 tag 源码包不等价。
- 在 OHOS 上用 `--host=aarch64-unknown-linux-ohos` 避免 Autoconf 执行尚未签名的探测程序。
- 构建、安装后的 ELF 用目标机的 `binary-sign-tool` 签名，再运行功能测试。
- 依赖制品仓已发布的 `htslib/1.24-r0` 与 `zlib/1.3.1`。

## 验证

上游无 Automake 注册测试；配方实际执行 4 个 README 命令示例（mapped、BAM、histogram、coverage），并由 `test_package` 对安装后的 `preseq` 做 1 项直方图外推测试。目标机单次冻结输入事务的 12 阶段记录为 `W3_PASS`。

[上游仓库](https://github.com/smithlabcode/preseq)
