# proxsmtp 1.10 HarmonyOS PC 验证记录

- 看板：`proxsmtp/1.10` 已由 `@tank_you` 认领，指定分支 `feat/proxsmtp-1.10`，活动「开源鸿蒙 PC 专项积分赛」。
- 上游：`http://thewalter.net/stef/software/proxsmtp/proxsmtp-1.10.tar.gz`，SHA-256 `33b13cb4cbbebd784768893404c992d6cc2e8d057c27c012e3a69f24ac60c4b5`。源码 `configure.in` 声明版本 1.10；`COPYING` 为三条款 BSD 风格条款。
- 真机：HarmonyOS PC AArch64，Conan 2.29.1；验证目录 `/data/storage/el2/base/haps/entry/files/proxsmtp-1.10-20260926T152934`。Windows 与目标机上游 tarball SHA-256 一致。
- 初始故障：发布包自带 2009 年 `config.guess` 不能推断 `HarmonyOS`；`config.sub` 也不识别 `aarch64-unknown-ohos`。配方携带 GNU config 项目 2026 年 `config.sub`（SHA-256 `f9a31e9a3f5b7cbeb8d8c3f2015895a51e7222130114c9c363fcbccd78e4bf6b`），显式同值 `--build=--host=aarch64-unknown-ohos`。真机 `configure` 显示 `cross compiling... no`，并实际运行编译与链接探针；不是交叉编译绕过。
- 独立能力探针：`--enable-capabilities --disable-tproxy` 配置失败，`cap_get_proc in -lcap... no`（`probe-cap.log` SHA-256 `76edf59d9f4079db0ec4b27479175902daa05931d130c5562cc20f615fe3e343`）；`--disable-capabilities --enable-tproxy` 配置与编译通过（`probe-tproxy.log` SHA-256 `eef0834df6437d20a53496d798e139f9a8986fdf249253d2364e4776e4592395`，`probe-tproxy-build.log` SHA-256 `6064169dc8305be8140617cbb7f0582472372b2d43f4a593f12335c0f2a05383`）。因此最终保留 `IP_TRANSPARENT` 编译、禁用缺失的 `libcap`；不推断特权透明运行模式已通过。
- 源码补丁：`spio.c` 满行分支写入 `line[SP_LINE_LENGTH]` 超出数组一字节，改为合法的末尾索引；`smtppass.c` 将目标机指针型 `pthread_t` 以 `%p` 记录，不再强转 `int` 后 `%x`。未修改上游测试，因为源码包无自动化测试用例。
- 最终验证：隔离 Conan home，`conan graph info --build=never` 无 Conan 依赖；`conan create ./recipe -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -c tools.build:jobs=1` 返回 0。新增 `test_package` 以安装包二进制运行 `-v`，再通过本地 SMTP 后端执行邮件转发，打印 `PASS: installed version and loopback SMTP relay`。最终 `create6.log` SHA-256 `9539b91214a6c6a61e77cac62ff2fdbb5b2dbcbcd6ead2eb2ba4f6a53afccc11`，无 Clang warning。ELF64 AArch64，动态依赖仅 `libc.so`。
- 范围：未进行外部网络邮件投递、筛选脚本、透明拦截的特权运行测试；不声称这些路径通过，也不声称 `libcap` 在所有 HarmonyOS PC 上均不可用。
