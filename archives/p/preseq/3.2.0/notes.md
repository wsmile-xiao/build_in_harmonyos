# preseq 3.2.0 适配笔记

- 构建环境：HarmonyOS PC aarch64，clang 15，Conan 2；2026-10-01。
- 源码：上游 `preseq-3.2.0.tar.gz` 正式发布包，SHA-256 `95b81c9054e0d651de398585c7e96b807ad98f0bdc541b3e46665febbe2134d9`。
- 依赖：htslib/1.24-r0、zlib/1.3.1（及 HTSlib 的 xz/libdeflate 传递依赖）。
- 配置：`--enable-hts --host=aarch64-unknown-linux-ohos`，然后 `make -j2`、`make check -j2`、`make install`。
- 首次冻结测试 `preseq-w3-20260930T155052Z` 在 configure 报 `cannot run C++ compiled programs`：目标系统拒绝运行未签名的 Autoconf 探测程序。加 `--host` 后重新冻结输入。
- 第二次测试 `preseq-w3-20260930T160025Z` 为 `W3_PASS`，12/12 阶段收据通过，构建日志 SHA-256 `a6c6a29cc83dea3afcb29f9d3222f71ae1267f7261c4e193d675fd5cec4de6c8`。
- 上游 Makefile 无 `TESTS` 或 `check_PROGRAMS`：`make check` 仅构建，不计为测试。配方运行 README 的 mapped、BAM、histogram、coverage 四种示例，4/4 有非空输出。
- README 的直方图文件名写为 `SRR1301329_1M_read.txt`，正式包实际是 `SRR1301329_1M_hist.txt`；配方只修正调用路径，不改上游数据。
- 安装后的签名 `preseq` 在 Conan `test_package` 中读取原始直方图，1/1 输出列及数据行检查通过。
