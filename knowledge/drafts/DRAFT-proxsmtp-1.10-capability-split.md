# ProxSMTP 1.10：libcap 缺失不等于 IP_TRANSPARENT 缺失

状态：知识库扩展草稿；是否构成独立路径 B 条目由维护者判定。已有 `knowledge/graph/E007.kv` 处理旧版 `config.guess`/`config.sub` 不识别 OHOS，本条不重复该事实，关注不同可选网络能力的证据边界。

## 现场现象与原因

ProxSMTP 1.10 的 `configure.in` 将 Linux capabilities 和真透明代理分成两组 `AC_ARG_ENABLE` / 能力检查。所测 HarmonyOS PC AArch64 上，以更新的 GNU `config.sub` 识别 `aarch64-unknown-ohos`、指定同值 build/host 后，`configure` 报告 `cross compiling... no`。在该前提下：

1. 显式 `--enable-capabilities --disable-tproxy` 返回 1：`checking for cap_get_proc in -lcap... no`，`Could not find the libcap2 libraries`。
2. 显式 `--disable-capabilities --enable-tproxy` 返回 0：`IP_TRANSPARENT is declared... yes`，随后 `make -j1` 返回 0。
3. 最终配方采用第 2 组开关，隔离 `conan create` 返回 0；安装包 `-v` 与回环 SMTP 邮件转发成功。

因此，这台机器上缺少 `libcap` 是单独的链接能力限制，不能把它扩大为 `IP_TRANSPARENT` 不可编译。反过来，编译通过也不能证明有权限配置套接字或完成透明转发；后者需要独立的特权和网络拓扑测试，本次未执行。

## 可复用诊断

- 先解决 E007 的平台识别，确认 `cross compiling... no` 或明确交叉编译语义，再讨论能力探针结果。
- 分别检查可选库链接、宏/头文件、相关代码路径编译、普通功能运行、特权功能运行；每层记录可核验的输出。
- 只禁用证据显示缺失的层，保留可编译层，并在 PR 中明确未运行的高权限路径。避免以“构建成功”冒称“全部运行功能通过”。

证据：上游 SHA-256 `33b13cb4cbbebd784768893404c992d6cc2e8d057c27c012e3a69f24ac60c4b5`；目标机验证目录 `/data/storage/el2/base/haps/entry/files/proxsmtp-1.10-20260926T152934`；失败 `probe-cap.log` SHA-256 `76edf59d9f4079db0ec4b27479175902daa05931d130c5562cc20f615fe3e343`；通过的配置/编译 `probe-tproxy.log`、`probe-tproxy-build.log` SHA-256 分别为 `eef0834df6437d20a53496d798e139f9a8986fdf249253d2364e4776e4592395`、`6064169dc8305be8140617cbb7f0582472372b2d43f4a593f12335c0f2a05383`；最终 `create6.log` SHA-256 `9539b91214a6c6a61e77cac62ff2fdbb5b2dbcbcd6ead2eb2ba4f6a53afccc11`。日志留在目标机，不含账号凭证的摘录见 PR/Issue。
