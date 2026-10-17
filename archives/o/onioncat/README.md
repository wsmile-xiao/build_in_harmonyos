# onioncat

OnionCat（ocat）— 在 Tor 隐藏服务（或 I2P 隧道）之上构建透明 IPv6 层的
VPN 适配器。将 onion 地址映射到 fd87:d87e:eb43::/48 ULA 段的 IPv6 地址，
通过 TUN/TAP 设备提供透明的 IP 层匿名传输。

- 上游: https://github.com/rahra/onioncat
- 作者: Bernhard R. Fischer <bf@abenteuerland.at>
- 许可: GPL-3.0-only
- 语言/构建: C / autotools（发布包不含 configure，需 autoreconf 引导）
- 产物: bin/ocat（单一命令行守护进程，无链接库）

## OHOS 适配要点

- 发布 tarball 无 configure：build() 内按上游 autogen.sh 序列
  （autoreconf -f → automake --add-missing --copy → autoreconf -f）引导，
  tool_requires autoconf/2.72 + automake/1.18（制品仓已发布）
- automake 1.18 的新版 config.guess 原生识别 HarmonyOS
  （aarch64-unknown-linux-ohos），无需 config.guess/config.sub 补丁
- E011：autoconf 生成的 configure/config.status 以 umask 077 创建临时
  目录，HMDFS setgid 目录组无写位导致 Permission denied —— build() 内
  将生成的 configure 中 umask 077 改写为 022（生成文件改写，非源码补丁）
- 零外部库依赖：pthread/socket 均由 OHOS libc（musl）提供
- 产物不 strip（llvm-strip 后 ELF 本平台 EACCES，olsrd 先例）
