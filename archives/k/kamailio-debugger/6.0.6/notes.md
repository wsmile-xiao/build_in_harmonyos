# kamailio-debugger 6.0.6 适配笔记

## 一、编译环境

- 构建系统: makefile（kamailio 经典 Makefile 体系，非 autotools/cmake）
- 编译日期: 2026-09-26
- 编译器: clang（`/data/service/hnp/bin/clang`，OHOS SDK 26.0.0.18，目标 `aarch64-unknown-linux-ohos`）
- 状态: published
- 依赖: 无（模块 Makefile 的 `LIBS=` 为空，纯 kamailio core 插件）
- 补丁: 无（`conandata.yml` 为 `patches: {}`）

## 二、编译步骤

```bash
# 1) 生成 src/config.mak（探测 aarch64-unknown-linux-ohos 目标）
make cfg include_modules=debugger

# 2) 仅构建目标模块
make modules modules=modules/debugger -j1
```

产物：`src/modules/debugger/debugger.so`（321,920 bytes），由配方安装到 `lib/kamailio/modules/`。

与同族 `kamailio-outbound` 的差异：outbound 需要在构建期钉死 `BUILDER=` / 传 `LOCALBASE=<openssl>`，
因为其 Makefile 会 `which pkg-config` 探测宿主 OpenSSL；debugger 模块 `LIBS=` 为空、**不做任何依赖探测**，
因此配方无需传任何 `XXXCFG=` 变量（同族 snmpstats 的 `SNMPCONFIG=`、unixodbc 的 `ODBCFG=` 在此不适用）。

## 三、遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 模块打包如何验证？本仓库同族先例（snmpstats/unixodbc）都在 test_package 里做 ELF + 加载实跑，debugger 无外部依赖头文件，ELF 校验不足以证明"可被 kamailio 加载" | `debugger.so` 是 kamailio core 插件，`.so` 自身不 NEEDED kamailio；只有在 dlopen 时才会解析它引用的 core 符号 | 在 `test_package/` 里实现**消费者 E2E**：提供 kamailio core 符号 shim（`kamailio_core_stub.c`，`-Wl,--export-dynamic` 导出），消费者进程 dlopen 模块 → dlsym 取 `exports` → 按 core ABI 读取 `module_exports` → 调用 `mod_init`/`child_init`，跑真实链路 |
| 2 | 消费者进程 dlopen 模块失败（未定义 core 符号） | OHOS/musl 无惰性绑定（`RTLD_LAZY` 等价 `RTLD_NOW`）：dlopen 那一刻就必须能解析模块的全部未定义符号 | shim 覆盖模块引用的全部 core 符号（日志/全局量/dlopen 辅助/内存分配等），并以 `-Wl,--export-dynamic` 链接，使符号进入动态符号表 |
| 3 | `kamailio_core_stub.h` 编译期报 `DEFAULT_DLFLAGS` 未定义 | 该宏在 core `src/core/sr_module.h:188` 定义，是模块 `dlopen` 标志的来源；shim 头未同步 | 按 core 真实定义补入 `DEFAULT_DLFLAGS`（模块源码 `dlopen(path, DEFAULT_DLFLAGS)` 依赖它） |
| 4 | 结构体布局风险 | 模块对 core ABI 结构体（`cmd_export_t`/`ksr_cmd_export_t`/`rpc_export_t`）`memset` 整结构体后按偏移赋值，字段顺序/数量不符会写坏栈 | shim 头逐字段对齐 core 定义（`core/sr_module.h:206-231`、`core/rpc.h:134-141`），消费者 E2E 通过该结构体读取 `mod_init`/`child_init` 指针 |
| 5 | 消费者用例如何避免"空壳测试" | 只断言符号存在无法证明模块可加载可用 | E2E 做**真实调用链**：dlopen → dlsym(`exports`) → `mod_init` → `child_init(PROC_INIT)`（触发 `dbg_enable_mod_levels`/`dbg_init_pid_list`）→ `dbg_init_rpc`（走 `rpc_register_array`），并含负例（不存在的 rpc 名不应被注册成功） |

## 四、上游测试清点（R51 三步法）

**清点面**：`kamailio-6.0.6_src.tar.gz` 内 `test/`、`tests/` 共 **4 个目录 / 17 个文件**
（10 个 `dbtextdb` 用例数据 + `janssonrpcc` 3 + `rtpproxy` 3 + `tm` 1）。

**可执行面**：仅 `utils/kamctl/dbtextdb/dbtextdb_test.py` 自包含（3 个 unittest 用例，仅依赖 Python 标准库），
已在配方 `build()` 末尾真实执行：**3/3 通过（100%）**。

**未执行面**：其余 14 项逐项技术原因登记于 `test_package/MANIFEST.yml` 的
`upstream_tests[].not_executed_reason`（多数需运行中的 kamailio 主程序或对端 SIP/RTP 环境，
`tm/kill_sem.sh` 需 root 且会清空宿主 SysV IPC，在共享 CI worker 上具破坏性）。

**模块自身**：`src/modules/debugger/` 无测试源、无 `check`/`ctest` 目标。

## 五、验证结果

```bash
# 消费者 E2E（dlopen → dlsym → mod_init → child_init → dbg_init_rpc，含负例）
== 结果：92 passed, 0 failed, 0 skipped ==
== ALL CHECKS PASSED ==

# 产物面检查（ELF/符号/依赖/许可，13 项断言）
== 结果：13 passed, 0 failed, 0 skipped ==
== ALL CHECKS PASSED ==

# 上游 unittest
Ran 3 tests in 0.014s   → OK
```

Conan 门禁：`G1 ✅ / G2 ✅ / G3 ✅ / G4 ✅`（`G3` 无系统同名库冲突，R26 通过）、`L2 ✅ / L4 ✅ / L5 ✅`。
包引用：`kamailio-debugger/6.0.6@ohpcd/stable`。

## 六、交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `lib/kamailio/modules/debugger.so` | 321,920 bytes | kamailio 运行时 `loadmodule` 加载的调试模块（无 RPATH/RUNPATH，DT_NEEDED 仅 libc.so） |
| `licenses/COPYING` | — | 上游 GPL-2.0 许可文本 |

## 七、注意事项

1. 本包**不依赖 kamailio 本体包**（模块导出的是运行时符号面），`cpp_info.libs` 为空，仅声明模块目录
   `lib/kamailio/modules`；无命令行可执行文件 → 按 R38 不声明 `commands.json`。
2. 模块**运行期行为**（断点、`dbg.pv_dump`、RPC 命令实际效果）未做端到端验证——需要运行中的 kamailio
   主程序与 SIP 消息流，不在本包制品范围内；E2E 验证的是"可加载 + 导出面 + 初始化链路"。
3. `conan create` 会在 `test_package/` 就地生成 `conanbuild.sh` / `conanrun.sh` / `deactivate_*.sh` /
   `metadata/` 与测试二进制，属构建产物，**提交前必须清理**（本包已清理，避免 JC 垃圾门禁误拦）。
4. 产物未 strip，调试字符串内含构建目录绝对路径（仅调试信息，与运行时依赖解析无关）。
---

**编译结束**: 2026-09-26 23:15
**最终状态**: published
