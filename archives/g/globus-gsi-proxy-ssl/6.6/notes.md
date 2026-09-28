# globus-gsi-proxy-ssl 6.6 适配笔记

## 来源与版本

- 上游项目：Grid Community Toolkit（GCT）的 GSI Proxy SSL 库，实现 PROXYCERTINFO / PROXYPOLICY 两个 ASN.1 结构的 DER 编解码（RFC 3820 代理证书扩展），供 X.509 证书扩展处理使用。
- 源码归档：https://deb.debian.org/debian/pool/main/g/globus-gsi-proxy-ssl/globus-gsi-proxy-ssl_6.6.orig.tar.gz（SHA256 见同目录 conandata.yml）。
- 版本状态：6.6 为最新 GCT v6.2.20260123 发布版所含组件版本；upstream master 的 6.7 尚未发布。
- 许可证：Apache-2.0。
- 依赖（单 flavor，无 thr/nothr 变体）：仅 openssl >= 1.0（本仓钉 openssl/3.5.6）；无 globus-common、无 libltdl。

## 编译环境

- 构建系统：autotools（源码自带预生成 configure，automake 1.11 生成，无需 autoreconf）
- 目标平台：HarmonyOS PC（OHOS），aarch64
- 编译器：clang
- triplet：--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos

## 适配要点

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 以 umask 077 运行，生成文件权限异常 | 上游脚本 mktemp / mkdir 两处 umask 077（automake 1.11 生成的旧式脚本），与鸿蒙环境权限语义冲突 | source() 阶段一次替换 umask 077 → umask 022，两处全覆盖 |
| 2 | configure 报无法识别的 host 类型，且存在静默错配风险 | 源码内 config.guess 2018-03-08 / config.sub 2018-05-05 不识别 *-linux-ohos；该版 config.sub 无 kernel-os 校验门，os 归一化大表若缺 -linux-ohos*，4 段三元组会被兜底 sed 静默改写为 -linux-gnu-ohos 且 rc=0 | 补丁 patches/0001-config.sub-ohos.patch，替换对形状三 hunk：maybe_os 列表行、linux-ohos 子分支（纯插入改写为相邻行 -/+ 替换对以兼容设备端 toybox patch）、os 归一化大表追加 -linux-ohos*（4 段三元组的必需 hunk）；补齐后 4 段/3 段输入均原样归一化为 aarch64-unknown-linux-ohos，并以 config.sub 输出断言收口 |
| 3 | 链接依赖面（正向确认，无需处理） | libglobus_proxy_ssl_la_LIBADD 仅 $(OPENSSL_LIBS)（-lssl -lcrypto），openssl 无 .la | 无需 .la 替换 hack（区别于 globus-common / globus-callout / globus-gsi-openssl-error 先例），configure 后直接 make |

## 上游测试与替代执行说明

- 上游测试：test/ 下 TESTS = test_pci.pl（perl 驱动 Test::More，TAP plan 1..20 = 5 用例 × 每用例 4 断言：encode 运行 / decode 运行 / DER 往返比对 / 两轮 stdout 自比），纯本地 DER 编解码回环，无网络/证书需求。
- `make check` 驱动在鸿蒙不可用：perl 驱动经 PATH 找到的是 libtool 包装脚本，其会重置 LD_LIBRARY_PATH，导致依赖共享库加载失败。
- 替代执行（零覆盖损失，不改上游测试文件与数据）：显式 `make test_pci` 构建 check_PROGRAMS 后，用 .libs 下真实 ELF 替换 libtool 包装脚本（仅替换构建产物），注入 LD_LIBRARY_PATH（openssl 包 lib + 本包 library/.libs）后由源码 test/ 下 perl 驱动直跑，实际运行 TAP 20/20 全 ok。该说明已同步记录于 manifest.yaml 与 conanfile.py 注释。

## 验证结果

- 权威 CI：ci/conan/build_and_test.sh + ohos-aarch64 profile，rc=0，Pass rate 100%（1/1）。
- 上游 TAP 测试：20/20 通过（100%）。
- test_package 消费者测试（L1）：构造 PROXYCERTINFO（path length + PROXYPOLICY 策略）→ i2d DER 编码 → d2i 解码 → 字段校验（path length / 策略字节 / 策略语言 OID）→ 解码结果二次 DER 编码与首次编码 memcmp 逐字节一致，真机 aarch64 通过；并通过破坏性负向测试（L1e）确认测试真实依赖本库。
- 门禁：L0/L1（含 L1e）/L4/L5 与 G0/G0e、知识库检查（KC/JC）通过；L2 skip（纯库，无 bin/ 可执行冒烟项）。

## 已知限制

- 仅在真机 aarch64 验证，模拟器未覆盖。
- 无其他已知限制。
