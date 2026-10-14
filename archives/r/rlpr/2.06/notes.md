# rlpr 2.06 适配笔记

- 源码：Debian 发布的上游原始源码包 `rlpr_2.06.orig.tar.gz`，SHA-256 `32ae5893f4b9250b7a02c98a41b5929cfdd5731b6efbd7edfc77c2c5314388f7`。
- 依赖：没有必须先发布的三方 Conan 依赖。上游 Autotools 配置脚本包含 `off_t` 运行探测；在鸿蒙上使用不同的合法 build/host 三元组，走其原有交叉编译分支，需在真机确认其猜测与目标 ABI 一致。
- 只调用普通 `make install`。额外的 `install-setuid`、`install-proxy` 和 `bsdlinks` 会改所有权、setuid 或 `/usr/bin`，不属于 Conan 包装流程。
- 上游 `make check` 没有注册的 `TESTS` / `check_PROGRAMS`，计为 0/0。消费者测试运行安装后的 4 个命令 `-V`，逐个核验 2.06 版本文本，4/4 通过；测试仅提供 `PRINTER=lp@127.0.0.1` 满足上游在解析 `-V` 前的配置检查，不连接打印机或启动代理。
- 首轮真机事务 `rlpr-w3-20261006T082658Z` 在 `configure` 阶段失败：验证 profile 的旧 Bash 路径在当前设备上不存在；同时上游 `config.sub` 不识别 `linux-musl`。新事务改用目标机现有 `/system/bin/sh`，配方在临时构建副本中为 `config.sub` 增加精确的 musl 分支。失败事务不追认通过。
- 后续独立事务逐项暴露旧 Autotools 对 `ld`、`ar` 的硬编码（设备提供 `ld.lld`、`llvm-ar`），以及目标机 UID 无 passwd 名称映射。配方将工具变量显式指向现有工具；仅在 OHOS 构建副本中、精确匹配的三个客户端源码里增加数值 UID 兜底，不信任 `USER`/`LOGNAME`。
- 最终独立事务 `rlpr-w3-20261006T090848Z` 在 `10.62.201.39:2222` 完成精确传输、独立回读、构建、签名、消费者测试和释放后校验，12/12 阶段收据通过。真机日志 SHA-256 `2310e68a2ef67a172e2ab2471cd8fd945c51e11b19343e12f89a02fde2d8ad49`，候选哈希 `b96000de5cbf0f81f0e45516bccae06c287fd5683beff159f3af9e27a68baf35`。
- 尚需知识草稿去重、Pre-PR 合约、Issue/PR 模板与平台校验；真机 W3 通过不等于比赛 CI 或真实打印任务通过。
