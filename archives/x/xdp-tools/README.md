# xdp-tools

XDP/eBPF 用户态工具集：

- `xdp-loader` —— 加载/卸载 XDP 程序到网卡；
- `xdp-filter` —— 基于 XDP 的包过滤；
- `xdpdump` —— 抓取 XDP 跟踪数据并写成 pcap/pcapng。

## Upstream

- Homepage: https://github.com/xdp-project/xdp-tools
- Version: 1.6.3（tag `v1.6.3`）
- License: GPL-2.0-only AND LGPL-2.1-only AND BSD-2-Clause（混合）

## HarmonyOS adaptation

手写 shell `configure` + GNU Make。配方消费已发布的 `libbpf/1.5.1`（`FORCE_SYSTEM_LIBBPF=1`）与
`libpcap/1.10.6`，并用 9 个 portability 补丁处理 OHOS/bionic 的 UAPI/libc 头差异。无 `bpftool` 时
只构建 `xdp-filter`/`xdp-loader`/`xdpdump`（上游既定行为）。上游集成测试需 root + netns + bpffs +
十余个网络工具，OHOS 无 BPF syscall，故如实申报为未执行（见 `1.6.3/test_package/MANIFEST.yml`）。

## Versions

| Version | Status | Conan ref |
|---|---|---|
| 1.6.3 | built | `xdp-tools/1.6.3` |
