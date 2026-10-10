# DRAFT-12592: OHOS 路径式 AF_UNIX socket bind 全面禁止与服务器类 gtest 套件的 GTEST_FILTER 排除方案

- **ID**: `DRAFT-12592-ohos-pathname-unix-socket-bind-denied-gtest-filter`
- **触发工具/阶段**: meson | conan | gtest — testing / runtime
- **严重度**: 2（🟡 中等）
- **类别**: ohos, gtest, sockets, portability, testing, environment-limits
- **来源**: isc-kea 3.0.3 适配（feat/isc-kea-3.0.3，OHOS PC aarch64，2026-10-08）

## 错误特征

```
29 个套件首跑：19 过 10 败
  6 × killed by signal 11 SIGSEGV   （0.16s~3.06s，套件中途崩）
  4 × exit status 1                 （用例级断言失败）
SIGSEGV 探针：caught signal 11 addr=0 pc=0x6534f615d0
  mapping: /system/lib/ld-musl-aarch64.so.1
  符号化：pc - load_bias = 0x1495d0 = strlen + 0x10
单用例直跑复现（无 MALLOC_PERTURB_ 亦稳定失败）：
  bind: Operation not permitted      （tmpfs，EPERM）
  bind: Permission denied            （hmfs，EACCES）
  Filename too long [system:36]      （sockaddr_un::sun_path 超长）
  unable to open '/tmp/leasefile6_1.csv'
  Result: failed to die              （death test）
  it throws nothing                  （chmod 语义）
  Non-matching addresses on the detected interface ip6_vti0
```

## 场景

`isc-kea`（ISC Kea 3.0.3 DHCP/DNS 服务器套件）的上游 gtest 覆盖 29 个套件
（24 个核心库 + 5 个服务器本体）。其中六个套件（kea-config / asiolink /
dhcp4 / dhcp6 / d2 / agent）的**控制通道测试**以路径式 AF_UNIX socket 为
基础：`ClientConnectionTest`、`UnixCommandMgrTest`、`UnixDomainSocketTest`、
`CtrlChannel{Dhcpv4,Dhcpv6,D2}Test`、`CtrlAgentCommandMgrTest` ——它们共同
使用上游 `testutils/sandbox.h` 的 Sandbox 夹具（`mkdtemp(P_tmpdir
"/kea-XXXXXX")` 构建用例专属临时目录）。

同源已交付的 kea-hooks / kea-perfdhcp / kea-hook-* 包**不受影响**，原因
唯一：它们的测试目录里没有 unix-socket 夹具——这反过来证明根因不在
编译产物而在平台环境边界。

## 根因（六类，全部实测验证）

1. **路径式 AF_UNIX bind 被 OHOS 全面禁止**（核心根因）：
   - 实测矩阵：tmpfs（`/storage/Users/...`）→ `EPERM`；hmfs（`/data/service/hnp`、
     `/data/app`）→ `EACCES`；`/dev`、`/dev/shm` → 拒绝；**抽象命名空间
     （`sun_path[0]=='\0'`）→ 成功**。
   - 传染链：夹具 `Sandbox::Sandbox()` 用 `mkdtemp(P_tmpdir "/kea-XXXXXX")`，
     OHOS 的 `/tmp` **只读**，`mkdtemp` 返回 NULL，随后 `std::string path_ = NULL`
     在 musl 加载器/`strlen(0)` 处 SIGSEGV（ucontext 探针实测：addr=0、
     PC 落在 `/system/lib/ld-musl-aarch64.so.1` 的 strlen+0x10；ptrace/gdb
     被拒，探针是唯一可用的崩溃定位手段）。
   - 排除 153 用例（七个 fixture，注册 154 含 1 个上游 DISABLED_）。
2. **只读 /tmp**：`MemfileLeaseMgrTest.dataDir*` 在 `/tmp` 开租约 CSV
   （报错定位 `unable to open '/tmp/leasefile6_1.csv'`），2 用例。
3. **conan 深构建目录超 `sockaddr_un::sun_path` 107 字符**：
   `Dhcp{4,6}ParserTest.comments`、`Dhcp{4,6}GetConfigTest.run/{69,65}`、
   `Http(s)CtrlChannel{Dhcpv4,Dhcpv6,D2}Test.configWriteFullPath`（后者经
   控制 socket 写配置，响应非 map：`get(string) called on a non-map
   Element`），10 用例。
4. **OHOS death-test 语义**：子进程死亡消息不回传父进程控制台
   （`Result: failed to die`），`FormatterTest.mismatchedPlaceholders`，1 用例。
5. **OHOS chmod(S_IRUSR) 不阻止属主写**：`open(O_WRONLY)` 仍成功
   （`it throws nothing`），`PIDFileTest.pidWriteFail`，1 用例。
6. **虚拟接口清单差异**：`ip6_vti0`/`ip6tnl0` 无匹配地址（`Non-matching
   addresses on the detected interface ip6_vti0`），`IfaceMgrTest.detectIfaces`，
   1 用例。

排除合计 **168** = 应执行 7294（注册 7321 − 上游 DISABLED 27）− 实际通过
7126，对账闭合。

## 推荐方案（实测配方形态）

```python
# conanfile.py 类属性：负向过滤清单（fixture 粒度，保住同套件内非 socket 用例）
_ohos_gtest_filter = (
    "-ClientConnectionTest.*:UnixCommandMgrTest.*:UnixDomainSocketTest.*"
    ":CtrlChannelDhcpv4SrvTest.*:CtrlChannelDhcpv6SrvTest.*"
    ":CtrlChannelD2Test.*:CtrlAgentCommandMgrTest.*"
    ":FormatterTest.mismatchedPlaceholders:PIDFileTest.pidWriteFail"
    ":IfaceMgrTest.detectIfaces"
    ":MemfileLeaseMgrTest.dataDirEnvVarOverride"
    ":MemfileLeaseMgrTest.dataDirExplicitOveride"
    # ...（sun_path 超长家族逐用例列出）
)

def build(self):
    ...
    test_env = Environment()
    if str(self.settings.os) == "OHOS":
        test_env.define("GTEST_FILTER", self._ohos_gtest_filter)
    with test_env.vars(self).apply():
        self.run('meson test -v --no-rebuild -C "{}" {}'.format(...))
```

关键机制：**meson test 把父环境透传给每个测试进程**（meson-logs/
testlog.txt 头部 "Inherited environment" 段可复核 GTEST_FILTER 已在列），
因此 conan 的 `Environment().define()` 注入能到达 gtest 二进制。

## 验证

- 对照实验（同一 build 目录）：无过滤 → 10 套件失败；加过滤 → **29/29
  套件 Ok，7126 用例 0 失败**，`conan create` exit 0。
- 干净重跑（conan remove 后全流程重建）：数字完全一致（29/29、7126、
  test_package 双 PASS）。
- 非 OHOS 平台：`settings.os != "OHOS"` 分支不注入过滤器，全量执行。

## 限制

- gtest 负向过滤套件内全 fixture 被滤时报 "Running 0 tests" 仍 rc=0，统计
  必须用 `--gtest_list_tests` 实测注册数对账，不能拿运行数当注册数。
- `KEA_SOCKET_TEST_DIR` 逃生门在本环境无效：即使指向可 bind 的应用沙箱
  目录（`/data/storage/el2/base/*`），Sandbox 的 `mkdtemp` 仍先在只读
  `/tmp` 上炸 NULL。
- 改造上游走抽象命名空间属深度适配，不在本方案范围。
