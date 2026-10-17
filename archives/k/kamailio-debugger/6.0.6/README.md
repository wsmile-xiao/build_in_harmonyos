# kamailio-debugger 6.0.6 — HarmonyOS PC 适配说明

## 1. 软件简介

`debugger` 是 SIP 服务器 [kamailio](https://www.kamailio.org/) 的内置调试模块，提供脚本追踪与运行时干预能力：

- **配置追踪**：`cfgtrace` 打印路由块中每个配置动作的执行轨迹（十六进制/行号/模块函数格式可选）。
- **断点与步进**：`dbg_breakpoint(mode)` 在脚本中设置断点，配合 `step_usleep`/`step_loops` 步进。
- **伪变量与消息转储**：`dbg_pv_dump([mask][,level])` 转储伪变量、AVP/XAVP；`dbg_sip_msg()` 转储原始 SIP 消息。
- **模块级日志控制**：`mod_level_mode`/`mod_facility_mode` 按模块名动态调整 debug 级别与 syslog facility。
- **RPC 接口**：`dbg.bp` / `dbg.ls` / `dbg.trace` / `dbg.set_mod_level` / `dbg.set_mod_facility` /
  `dbg.get_mod_level` / `dbg.get_mod_facility` / `dbg.reset_msgid`。

产物为可由 kamailio 主程序在运行时加载的共享模块 `debugger.so`。

### 开源信息

| 项 | 值 |
|---|---|
| 软件名 | kamailio（模块：debugger） |
| 上游版本 | **6.0.6** |
| 上游仓库 | `https://github.com/kamailio/kamailio` |
| 官方源码 | `https://www.kamailio.org/pub/kamailio/6.0.6/src/kamailio-6.0.6_src.tar.gz` |
| 源码 sha256 | `32e4290c6813c9d0289abe9ec2de9138e12e0381179218a7fed374ad813ecc48` |
| 开源许可 | **GPL-2.0**（上游 `COPYING`；制品内随包分发于 `licenses/COPYING`） |

## 2. 适配范围（打包口径）

- 取**官方全量源码包**构建，**仅编译打包 `modules/debugger`**（与本仓库同族先例 `kamailio-snmpstats`、
  `kamailio-unixodbc`、`kamailio-outbound` 一致）。
- **不依赖 kamailio 本体包**：模块导出的是 kamailio 运行时符号面，由主程序在运行时解析；因此配方
  `cpp_info.libs` 为空，仅声明模块安装目录 `lib/kamailio/modules`。
- 产物**不含命令行可执行文件** → 按 R38 不声明 `commands.json`。
- 无补丁：`conandata.yml` 中 `patches: {}`。

## 3. 构建要点

kamailio 6.0.6 使用经典 Makefile 体系（非 autotools/cmake），交叉编译分两步：

```bash
# 1) 生成 src/config.mak（探测 aarch64-unknown-linux-ohos 目标）
make cfg include_modules=debugger

# 2) 仅构建目标模块
make modules modules=modules/debugger -j1
```

`src/modules/debugger/Makefile` 的 `LIBS=` 为空——debugger 是**纯 kamailio core 插件**，无外部库依赖，
也不做 `which pkg-config` 之类的依赖探测，因此无需像同族模块那样用 `BUILDER=`/`ODBCCFG=`/`SNMPCONFIG=`
钉死探测分支。依赖：无。

## 4. 验证结果

| 项 | 结果 |
|---|---|
| 编译（`aarch64-unknown-linux-ohos` clang，OHOS SDK 26.0.0.18） | 通过 |
| Conan 门禁 G1/G2/G3/G4 | PASS |
| CI L2 / L4 / L5 | PASS |
| 上游测试 | `utils/kamctl/dbtextdb/dbtextdb_test.py` 实跑 **3/3 通过（100%）** |
| 消费者 E2E（`test_package/test_debugger_e2e.c`） | **92/92 断言通过**：dlopen 模块 → dlsym `exports` → 按 core ABI 读取 `module_exports` → `mod_init` → `child_init(PROC_INIT)` → `dbg_init_rpc`（含负例） |
| 产物面检查（`test_package/check_debugger.py`） | **13/13 断言通过**：ELF 魔数/`ELFCLASS64`、`ET_DYN`、`e_machine=AArch64(0xB7)`、32 个关键导出符号、无 glibc 版本化符号、`NEEDED` 仅 `libc.so`、无 RPATH/RUNPATH、`licenses/COPYING` 存在 |
| 产物 | `lib/kamailio/modules/debugger.so`，321,920 bytes，无 RPATH/RUNPATH |

**为什么消费者用例是"实跑"而非纯断言**：`debugger.so` 不 NEEDED kamailio 本体，仅在 `dlopen` 时解析其引用的
kamailio core 符号；而 OHOS/musl 无惰性绑定（`RTLD_LAZY` 等价 `RTLD_NOW`），因此用例必须自行提供 core 符号
shim（`test_package/kamailio_core_stub.{h,c}`，`-Wl,--export-dynamic` 导出）才能真正加载模块并调用其入口。

上游测试清点：`test/`、`tests/` 共 4 目录 17 文件；其中 1 个自包含可执行测试已实跑，其余逐项技术原因登记于
`test_package/MANIFEST.yml` 的 `upstream_tests` / `not_executed_reason`。

## 5. 已知限制

1. 模块**运行期行为**（断点命中、配置追踪输出、RPC 命令实际效果）未做端到端验证——需要运行中的 kamailio
   主程序与真实 SIP 消息流，不在本包制品范围内；E2E 覆盖的是"可加载 + 导出面完整 + 初始化链路可执行"。
2. 上游 14 项测试未执行（原因见上）：多数需运行中的 kamailio 主程序，或属其他模块，或为纯数据/配置；
   `tm` 模块的 `kill_sem.sh` 需 root 且会 `ipcrm` 清空宿主 SysV IPC，在共享 CI worker 上具破坏性。
3. 产物未 strip，调试字符串内含构建目录绝对路径。

## 6. 目录说明

```
6.0.6/
├── conanfile.py                  # Conan 配方（CI 输入）
├── conandata.yml                 # 源码地址 + sha256 + 补丁声明（CI 输入）
├── test_package/                 # Conan L1 消费者测试（CI 输入）
│   ├── conanfile.py              # 编译并运行 E2E 消费者用例
│   ├── kamailio_core_stub.h      # kamailio core 最小类型/宏（ABI 对齐）
│   ├── kamailio_core_stub.c      # core 未定义符号 shim（-Wl,--export-dynamic）
│   ├── test_debugger_e2e.c       # 消费者 E2E：dlopen → mod_init → child_init → dbg_init_rpc
│   ├── check_debugger.py         # ELF/符号/依赖/许可 13 项断言
│   └── MANIFEST.yml              # 上游测试清点台账
├── patches/                      # 空（无补丁）
├── manifest.yaml                 # 编译元数据
├── notes.md                      # 适配笔记（构建要点/踩坑/证据）
└── reports/                      # conan-verify 报告、测试报告、conan create 日志
```
