# net-snmp 5.9.5 适配笔记

## 编译环境
- 构建系统: Autotools
- 编译日期: 2026-05-20
- 编译器: clang 15.0.4
- 状态: built

## 依赖
- openssl/1.1.1w

## 配置选项
```bash
./configure --prefix=$HOME/usr/local \
            --with-openssl=$HOME/usr/local \
            --with-defaults \
            --disable-embedded-perl \
            --without-ethtool
```

## 遇到的问题

### HarmonyOS 头文件冲突
- 问题：linux/socket.h 与 sys/socket.h 的 sockaddr_storage 重定义
- 解决：定义 __kernel_sa_family_t 并阻止 _UAPI_LINUX_SOCKET_H 宏

## 知识提取
- HarmonyOS SDK 头文件需要特殊处理以避免重定义冲突

## 2026-09-27 复核（Conan 配方化）

本次为 5.9.5 补齐 Conan 配方（此前只有 manifest/notes，无 conanfile.py），
并以 `conan create` 在 OHOS aarch64 profile 下完整复现。

### 与 5.9.4（已发布）的配方差异

1. **补丁不再需要**：5.9.4 带 `patches/0001-fd-mask-type-for-musl.patch`（给
   `configure` 的 `fds_bits` 类型探测补 `long` / `unsigned long`，musl 的
   `fd_set` 用的是 `unsigned long`）。5.9.5 上游**已自行修好**该探测：

   ```
   5.9.4 补丁前: for type in __fd_mask __int32_t unknown; do
   5.9.5 上游原貌: for type in __fd_mask __int32_t long 'unsigned long' unknown; do
   ```

   直接把 5.9.4 的补丁套到 5.9.5 上会 `Hunk #1 FAILED`（上下文行已变）。
   故 5.9.5 的 `conandata.yml` 中 `patches` 为空。

2. **configure 参数**与 5.9.4 保持一致（`--with-defaults` / `--disable-agent` /
   `--disable-applications` / `--disable-manuals` / `--disable-scripts` /
   `--without-perl-modules` / `--with-openssl=<pkg>`），交叉编译三元组
   `--build/--host=aarch64-unknown-linux-musl` 由 `AutotoolsToolchain` 之外显式补。

3. **依赖**：`openssl/3.5.6`（5.9.4 配方写的是 1.1.1w；制品仓中 3.5.6 已发布）。

### 踩坑：test_package 找不到 openssl 头

现象：

```
net-snmp/library/scapi.h:14:10: fatal error: 'openssl/ossl_typ.h' file not found
```

根因（两层）：

- **`cpp_info.includedirs` 返回的是相对路径**（`"include"`）。在 test_package 里
  直接拼 `-Iinclude`，编译器会到**测试包自己所在的目录**去找，而不是依赖包目录。
  必须用 `dependencies[ref].package_folder` 或 generator 把它绝对化。
- **openssl 是传递依赖，不在 test_package 的 `self.dependencies` 迭代里**，
  于是它的头路径压根没被加进 `-I` 列表。net-snmp 的**公开头**
  （`net-snmp-includes.h` → `snmpv3_api.h` → `library/scapi.h`）里就
  `#include <openssl/ossl_typ.h>`，所以拿 net-snmp 头的消费者**必须**同时
  拿到 openssl 的头。修法：test_package 的 `requirements()` 里显式
  `self.requires("openssl/3.5.6")`。

顺带记：`aggregated_components()` **不会**把相对路径绝对化（那是 generator 的
职责），别指望它在 test_package 里直接可用；它返回的是聚合后的 `CppInfo`
对象，**不是**可迭代的组件列表。

### 验证结果

`conan create archives/n/net-snmp/5.9.5 --version=5.9.5 -pr:h=ci/conan/profiles/ohos-aarch64`

- 主包：`Package '755d22deb2b25e0c2607a4d12a7d0b92f80f3bb5' created` ✅
- test_package 三项探针全绿 ✅
  - `./test_probe` → `net-snmp 5.9.5: 全部断言通过`
  - `bin/net-snmp-config --version` ✅（ezsnmp 这类消费方靠它取编译参数）
  - `bin/net-snmp-config --libs` ✅

构建期 `libtool: ldconfig: command not found` 为非致命噪声（交叉编译不需要
宿主 ldconfig）。
---

**编译结束**: 2026-09-27 14:11
**最终状态**: built

## 2026-09-28 复核（上游测试实跑 + 鸿蒙 PC 端到端）

### 勘误：上游是有测试的，之前的清点是方法错了

2026-09-27 那次按 `tests/` 目录 + ctest/pytest 注册去找，得出"上游无测试"——
**错的**。net-snmp 的测试套件在 `testing/fulltests/`，由 perl 驱动脚本 + C 单元
测试组成，没有任何 ctest 注册。逐组清点（165 例）：

| 组 | 用例数 | 形态 |
|----|-------|------|
| default / snmpv3 / tls / transports | 88 / 4 / 23 / 8 = **123** | 进程级集成测试（需 `snmpd`/`snmpget` 等程序） |
| unit-tests | **35** | C 单元测试（只调 libnetsnmp 的 C API） |
| perl | 6 | Perl 模块测试 |
| read-only | 1 | 只读会话集成测试 |

123 例集成测试要跑起来必须有 `snmpd`/`snmpget`/`snmpwalk`，而本配方是**依赖项形态**
（`--disable-agent --disable-applications`）不产出这些程序 → 不具备运行前提。
35 例 C 单元测试可以跑 → 本次实跑的就是这一组。

### 实跑方式

上游 `unit-tests` 由 `testing/fulltests/support/` 的 `clib_build` /
`cagentlib_build` / `capp_build` 三个包装器编译驱动（它们依赖完整构建树的
`libtool` 与 `net-snmp-config --build-command`）。设备上完整构建树走不通（见下），
于是**按三个包装器的真实 include/链接集合复刻编译命令**，直接拿 `conan create`
产物的头与库编译，在鸿蒙 PC 上真跑。原始日志留在
`/storage/Users/currentUser/tmp/nstest/ut/`（`results.tsv` / `results2.tsv`）。

### 结果：27/35 通过（19,775 条断言），8 例受限

未通过 8 例的归因（逐项技术原因，详见 `reports/test-report.md` §2.4）：

- `T002`/`T013`：上游包装器不 include `net-snmp/library/container.h`，而
  `net-snmp-includes.h` 也不传递包含它 → `netsnmp_str_compare` 未声明。上游在
  **构建树内**编译时靠 `-I$builddir/include` 命中，脱离构建树不可复现。
- `T024`/`T104`：链接期 `undefined symbol: run_exec_command` / `agentx_parse` ——
  依赖项形态未构建 AgentX 与 `utilities/execute` 两个 mibgroup 模块。
- `T004`/`T020`/`T026`/`T027`：**平台只读文件系统**。实测 `touch /tmp/x` 与
  `touch /etc/x` 都报 `Read-only file system`；这 4 例分别要写
  `/tmp/snmp-enum-unit-test-*`、`/etc/net-snmp/T020.conf` 等。
  → 这条反而印证了"本包的纯网络/纯内存路径不受平台只读文件系统影响"。

### 鸿蒙 PC 特有端到端测试（新增到 test_package/test.c）

之前 5.9.4 留下的 test.c 三组断言都是**纯内存**功能，验的是算法。新增第 4 组
`test_harmonyos_udp_loopback_e2e()`，验的是**平台链路**：

自己开一个 `127.0.0.1` 的 UDP socket 充当"代理侧"，用被测库按 ezsnmp 的调用序列
（`snmp_sess_init → snmp_open → snmp_pdu_create → snmp_add_null_var →
snmp_synch_response`）发一个 `sysDescr.0` 的 v2c GET，然后断言三件事：

1. 请求**真的**进了内核网络栈（回环 socket 收得到 43 字节，收不到即失败）；
2. 线上报文 BER 逐字节形状正确（`0x30` SEQUENCE、`02 01 01`=v2c、`public`、
   `0xa0` GetRequest、`sysDescr.0` 的 OID 编码 `2b 06 01 02 01 01 01 00`）；
3. 无人应答时正确返回 `STAT_TIMEOUT`，不挂死也不误报成功。

刻意**不碰文件系统**——正因为设备 `/tmp`、`/etc` 只读（上面那 4 例的死因）。

设备实测输出：

```console
$ ./test_probe
OID 往返 OK: 1.3.6.1.2.1.1.1.0 -> 9 个子标识 -> "iso.3.6.1.2.1.1.1.0"
GET PDU 构造 OK: 1 个 ASN_NULL varbind，OID 长度 9
会话初始化 OK: version/retries/timeout 均为默认值，脏数据已被覆盖
鸿蒙 PC 端到端 OK: udp:127.0.0.1:54099 上真实发出 43 字节 v2c GET（BER 形状校验通过），无应答时正确返回 STAT_TIMEOUT
net-snmp 5.9.5: 全部断言通过
$ echo $?
0
```

### 踩坑：HMDFS 上跑不了完整 configure

试过在设备上跑完整 `./configure` 以复现上游构建树，结论：**不可行**——`config.status`
执行 awk 辅助脚本时被 HMDFS 权限挡住，且 configure 本身耗时约 4.7h。故转为
"用 conan 产物复刻上游包装器编译" 的路线（上面实跑方式），结果一样可信且可复现。

### 设备环境事实（供后续适配复用）

- `/tmp` 只读、`/etc` 只读（`touch` 都报 `Read-only file system`）。
- 设备原生 `perl 5.42` 可用（上游 perl 组测试的前提，但本配方没开 perl 模块）。
- 本机 Python 子进程裸调 `git` 会 `FileNotFoundError`（`git` 是
  `/data/service/hnp/bin/git` 的符号链接）→ 需要绝对路径解析，已另开框架 PR
  #13605（与本包 PR 无关，已从本分支剥离）。
