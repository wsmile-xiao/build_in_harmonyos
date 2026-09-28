# kamailio-outbound 6.0.6 — HarmonyOS PC 适配说明

## 1. 软件简介

`outbound` 是 SIP 服务器 [kamailio](https://www.kamailio.org/) 的一个内置模块，实现 **SIP Outbound（RFC 5626）** 能力：注册流的连接复用、连接失效探测（keep-alive / CRLF ping）、以及 GRUU 与 flow-token 的关联处理。产物为可由 kamailio 主程序在运行时加载的共享模块 `outbound.so`。

- 上游版本：**6.0.6**
- 上游源码：`https://www.kamailio.org/pub/kamailio/6.0.6/src/kamailio-6.0.6_src.tar.gz`
- 源码 sha256：`32e4290c6813c9d0289abe9ec2de9138e12e0381179218a7fed374ad813ecc48`
- 开源许可：**GPL-2.0**（上游 `COPYING`；制品内随包分发于 `licenses/COPYING`）

## 2. 适配范围（打包口径）

- 取**官方全量源码包**构建，**仅编译打包 `modules/outbound`**（与本仓库同族先例 `kamailio-snmpstats`、`kamailio-unixodbc` 一致）。
- **不依赖 kamailio 本体包**：模块导出的是 kamailio 运行时符号面，由主程序在运行时解析；因此配方 `cpp_info.libs` 为空，仅声明模块安装目录 `lib/kamailio/modules`。
- 产物**不含命令行可执行文件** → 按 R38 不声明 `commands.json`。
- 无补丁：`conandata.yml` 中 `patches: {}`。

## 3. 构建要点

kamailio 6.0.6 使用经典 Makefile 体系（非 autotools/cmake），交叉编译分两步：

```bash
# 1) 生成 src/config.mak（探测 aarch64-unknown-linux-ohos 目标）
make cfg include_modules=outbound LOCALBASE=<openssl 包目录>

# 2) 仅构建目标模块
make modules modules=modules/outbound -j1 LOCALBASE=<openssl 包目录>
```

关键点：`src/modules/outbound/Makefile` 在 `CROSS_COMPILE` 为**空**时才执行 `BUILDER=$(shell which pkg-config)` 探测；交叉编译下该探测不可用，因此配方显式传空 `BUILDER=`（并传 `LOCALBASE=<依赖包目录>`）以钉死 `-I$(LOCALBASE)/ssl/include` + `-L$(LOCALBASE)/lib -lssl -lcrypto` 回退分支。已在 `src/config.mak` 核验 `pkgconfig_libssl=absent`、`sys_libssl=` 为空。

依赖：`openssl/3.5.6`（构建期；OpenSSL 符号在模块内静态吸收）。

## 4. 验证结果

| 项 | 结果 |
|---|---|
| 编译（`aarch64-unknown-linux-ohos` clang，OHOS SDK 26.0.0.18） | 通过 |
| Conan 门禁 G1/G2/G3/G4 | PASS |
| CI L4 / L5 | PASS（L2 跳过：纯模块包无 `bin/`） |
| 上游测试 | `utils/kamctl/dbtextdb/dbtextdb_test.py` 实跑 **3/3 通过（100%）** |
| **鸿蒙特有测试（完整消费者端到端用例）** | **69/69 断言通过**（`test_package/test_outbound_e2e.c`）：`dlopen` 真实加载模块 → 读 `exports` 导出表 → `mod_init` → `bind_ob` → `encode_flow_token`/`decode_flow_token` 往返（独立 base64 解码器交叉验证 23B/47B 布局，IPv4/IPv6 双分支）→ `use_outbound` → `destroy`（shm/pkg 分配释放平衡）；含空 token/长度非法/HMAC 篡改等负例 |
| 产物结构测试（`test_package/check_outbound.py`） | **12/12 断言通过**：ELF 魔数/`ELFCLASS64`、`ET_DYN`、`e_machine=AArch64(0xB7)`、模块导出符号、无 glibc 版本化符号、`NEEDED` 仅 `libc.so`、无 RPATH/RUNPATH、`licenses/COPYING` 存在 |
| 产物 | `lib/kamailio/modules/outbound.so`，4,512,128 bytes，无 RPATH/RUNPATH |
| W4 Pre-PR 审计 | `verdict=pass`（P0=0 / P1=0，详见 `reports/`） |

上游测试清点：`test/`、`tests/` 共 4 目录 17 文件；其中 1 个自包含可执行测试已实跑，其余逐项技术原因登记于 `test_package/MANIFEST.yml` 的 `upstream_tests` / `not_executed_reason`。

## 5. 已知限制

1. 模块的 **flow-token 编解码路径已由消费者端到端用例真实覆盖**（HMAC-SHA1-80 + base64、IPv4/IPv6 双分支、HMAC 篡改与非法长度负例）；仍未被覆盖的是**需要运行中的 kamailio 主程序与对端 SIP 环境**的行为（SIP outbound 会话保持、CRLF keep-alive、GRUU 注册），不在本包制品范围内。
2. 上游 16 项测试未执行（原因见上）：多数需运行中的 kamailio 主程序，或属其他模块，或为纯数据/配置；`tm` 模块的 `kill_sem.sh` 需 root 且会 `ipcrm` 清空宿主 SysV IPC，在共享 CI worker 上具破坏性。
3. 产物未 strip，调试字符串内含构建目录绝对路径。

## 6. 目录说明

```
6.0.6/
├── conanfile.py            # Conan 配方（CI 输入）
├── conandata.yml           # 源码地址 + sha256 + 补丁声明（CI 输入）
├── test_package/           # Conan L1 消费者测试（CI 输入）
│   ├── conanfile.py            # test()：先跑产物结构校验，再编译并实跑端到端用例
│   ├── test_outbound_e2e.c     # 鸿蒙特有测试：完整消费者端到端用例（69 断言）
│   ├── kamailio_core_stub.c    # 消费者进程内 core 符号层（分配器/配置/日志/base64 表）
│   ├── kamailio_core_stub.h    # core ABI 最小复刻（编译期 _Static_assert 复核）
│   ├── check_outbound.py       # ELF/符号/依赖面 12 项断言
│   └── MANIFEST.yml            # 上游测试清点台账（含 e2e_assertion_count）
├── patches/                # 空（无补丁）
├── manifest.yaml           # 编译元数据
├── notes.md                # 适配笔记（打包口径/踩坑/证据）
└── reports/                # conan-verify 报告、测试报告、W3 本地 CI 日志、W4 审计结果
```
