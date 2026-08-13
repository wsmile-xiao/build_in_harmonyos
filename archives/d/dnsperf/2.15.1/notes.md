# dnsperf 2.15.1 适配笔记

## 上游信息

- 库：dnsperf（DNS 性能测试工具集：dnsperf、resperf、resperf-report）
- 版本：2.15.1（2026-04-15，修复 DoH 响应处理 bug）
- 维护方：DNS-OARC（原 Nominum/Akamai；上游 GitHub 仓已归档，迁至 Codeberg）
- 许可证：Apache-2.0
- 构建系统：GNU Autotools

## 编译环境

- 编译日期：2026-08-13
- 编译器：clang 15（OHOS 工具链，由 conan profile conf `tools.build:compiler_executables` 提供）
- 平台：aarch64 / HarmonyOS（HongMeng Kernel）
- Conan：OHOS 适配版 2.29.1（profile: ci/conan/profiles/ohos-aarch64）

## 依赖

| 依赖 | 版本 | 必需 | 说明 |
|------|------|------|------|
| openssl | 3.5.6 | 是 | TLS（DoT/DoH）；configure 硬性 PKG_CHECK_MODULES |
| concurrencykit | 0.7.2 | 是 | 无锁并发结构（ck_ring/ck_pr） |
| libnghttp2 | 1.70.0 | 是 | DoH（HTTP/2） |
| json-c | 0.18 | 可选，已启用 | datafile JSON 输出 |
| ldns | — | 可选，未启用 | dynamic update；ohpcd remote 无包，configure 优雅降级 |

## 遇到的问题与解决方案

| # | 问题 | 原因 | 解决 |
|---|------|------|------|
| 1 | configure 校验三元组失败 | 自带 config.sub 不认识 `linux-ohos` | 0001 补丁：config.sub 增加 ohos* 分支 |
| 2 | Autoconf 临时目录创建失败 | HMDFS 上 `mktemp -d "./confXXXXXX"` + umask 077 不可写 | 0002 补丁：临时目录改到 `${TMPDIR:-.}` 且 umask 022 |
| 3 | PKG_CHECK_MODULES 模块名不匹配 | 依赖包 .pc 按 conan 包名生成（openssl.pc），configure 查询模块名 libssl/libcrypto/ck | build() 中按模块前缀直接注入 `<prefix>_CFLAGS/_LIBS` 环境变量（pkg-config 宏优先使用），路径取自依赖包 |
| 4 | config.guess 在 HMDFS 上探测失败 | configure 原生探测运行 config.guess | OHOS 原生构建时显式传 `--build/--host=aarch64-unknown-linux-ohos`（nsd 4.15.0 同款做法） |

## 上游测试

`make check`（src/test/ 下 7 个 shell 脚本）：

- 无网络环境（官方 CI 配置）：**7/7 PASS**。test1/3/7 的本地部分真实运行
  dnsperf/resperf 二进制；test2/4/5/6 经 `TEST_DNSPERF_WITH_NETWORK` 守卫
  跳过（上游脚本设计，exit 0）
- 本设备带网络附加验证（TEST_DNSPERF_WITH_NETWORK=1）：5/7 PASS。
  - test2 FAIL：dynamic update 子测试需要 ldns（本移植有意不引入，
    configure 优雅降级 "Unable to dynamic update, support not built in"）；
    其余 UDP/TCP/DoT/TSIG 查询子测试均通过
  - test5 FAIL：上游脚本依赖外部辅助服务器 dumdumd（上游 CI 预装），
    设备未安装；且脚本 `which dumdumd` 无 `|| true`，set -e 下直接退出
    （上游脚本假设 dumdumd 存在）

## Consumer 测试（test_package）

10 项断言全部通过：dnsperf/resperf -h、-O suppress 参数校验、
v2.11.0 长选项回归（issue #234）、DoH 选项组合、无效参数错误路径、
空 blob 输入拒绝（"Error: input file contains no data"）。

负向断言使用显式 `if cmd; then FAIL; exit 1; fi` 模式：POSIX sh 中
`set -e` 会忽略以 `!` 开头 pipeline 的失败，裸 `! cmd` 在二进制意外
返回 0 时不会使脚本退出（上游 test1/test3 同款写法存在同样问题，本
consumer 测试已强化）。已用"恒返回 0 的 stub 二进制"反向验证：脚本
正确以非零退出并打印 FAIL。

## 注意事项

- 上游 GitHub 仓库已归档（2026-02-04），官方发布渠道为 dns-oarc.net 文件服务器
- resperf-report 为 perl 脚本，运行时需 perl 环境
- 二进制为动态链接产物，HarmonyOS 上执行受 ELF 签名机制约束
