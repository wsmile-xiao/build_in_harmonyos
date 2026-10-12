# OHOS 拒绝 AF_UNIX 路径名 bind 时的 gtest 粒度跳过（同型探针 + GTEST_SKIP）

## 场景

kea-dhcp6 3.0.3（ISC Kea 的 DHCPv6 服务器）在 OHOS aarch64 上 `conan create`，
`build()` 内 `meson test` 实跑上游两套件：
`kea-dhcp6-tests`（gtest 单二进制，965 例）+ `dhcp6_process_tests.sh`（进程级 shell 套件，14 例）。

首轮 gtest **45 例 FAIL**（全部 `CtrlChannelDhcpv6SrvTest` 的 unix 命令通道用例），
另有 2 个 config-commit 用例因配置含 unix control socket 失败。

## 症状

失败输出形如：

```
[ RUN      ] CtrlChannelDhcpv6SrvTest.<通道类用例>
... cmd_ctrl / unix socket bind 失败: Operation not permitted
[  FAILED  ] ...
[  PASSED  ] ...（同套件其余用例全绿）
```

失败链（Kea 3.0.3 源码）：

1. 测试 `setSocketTestPath()` 在临时目录下配置 unix 命令通道；
2. `UnixCommandMgr` 打开控制通道 → `UnixSocket::bind()` 路径名套接字；
3. `bind()` 返回 **EPERM（Operation not permitted）** → 通道起不来，用例失败。

**45 例整组失败与用例逻辑无关**——同套件其余 900+ 例全绿，且 HTTP 控制通道
的测试全绿；失败率正好等于"建 unix 控制通道"的用例数。

## 根因

鸿蒙用户存储 `/storage/Users/currentUser` 是 **hmdfs 挂载**：对 AF_UNIX
**路径名**套接字的 `bind()` 返回 `EPERM`；`/tmp` 是只读挂载（`EROFS`，
普通文件也写不了）。实测（设备真机探针）：

| 目标 | 结果 |
|------|------|
| `/tmp/*.sock` | ❌ EROFS（只读挂载） |
| `$HOME` / conan 构建树（hmdfs） | ❌ EPERM（Operation not permitted） |
| TMPDIR 下（仍属 hmdfs） | ❌ EPERM —— **改路径不解决** |
| TCP 回环 `127.0.0.1` | ✅ bind 正常 |

关键：**目录"可写"不等于"可 bind"**。把 socket 目录改到 TMPDIR/cwd 的
"换路径"修法在本平台无效（raul 2.0.0 初版即踩此坑）。挂载点级白名单的
完整实测（含 `/dev/shm` EACCES、唯一例外 `/data/storage/el1/base`、抽象
命名空间全通）见相关条目 [[DRAFT-ohos-agent-socket-tmpdir-only-bindable-path]]。

对 kea-dhcp6 而言 unix 控制通道（kea-ctrl-agent ↔ 服务器）是**真实产品功能**，
不是测试夹具——平台不支持它，服务器其余功能不受影响。

## 怎么快速看出来

```bash
# 症状一句话定位：失败用例全部集中在控制通道 fixture
grep -c "FAILED.*CtrlChannelDhcpv6SrvTest" <build_folder>/meson-logs/testlog.txt
# 真机探针（"实际可用目录"里做真实 bind，10 秒出结论）
python3 - <<'PY'
import os, socket
d = os.environ.get('TMPDIR') or '/tmp'
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
try:
    s.bind(os.path.join(d, 'kea-probe.sock')); print('AF_UNIX_OK')
except OSError as e:
    print('AF_UNIX_FAIL', e)     # EPERM（hmdfs）/ EROFS（/tmp）
PY
```

可区分性：这是**平台能力缺失**（同型 bind 探针 EPERM），不是路径权限、
不是库缺陷；与 E024（SELinux 限制 + 建议 TCP 化）同根异面。

## 修复

**同型 bind 探针 + 粒度 GTEST_SKIP**（gtest 单二进制一次跑完所有用例，
meson 层的 exit 77 跳过机制**不可用**——这是与独立测试二进制场景的核心区别）：

```cpp
// 探针：放在共享测试工具（dhcp6_test_utils）里，供所有套件复用
bool BaseServerTest::unixControlSocketsUsable() {
    std::string probe_path = UnixCommandConfig::getSocketPath() + "/kea6-socket-probe";
    struct sockaddr_un addr; memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    if (probe_path.size() >= sizeof(addr.sun_path)) return (false);  // ENAMETOOLONG 类宿主
    memcpy(addr.sun_path, probe_path.c_str(), probe_path.size());
    int fd = ::socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) return (false);
    ::unlink(probe_path.c_str());
    bool usable = (::bind(fd, (sockaddr*)&addr, sizeof(addr)) == 0);
    ::close(fd); ::unlink(probe_path.c_str());
    return (usable);
}
```

跳过分两个层级（断言与用例注册数零改动）：

```cpp
// 组级：fixture SetUp 一次覆盖整组 45 例
void SetUp() override {
    if (!unixControlSocketsUsable())
        GTEST_SKIP() << "unix control channel requires AF_UNIX pathname sockets, "
                        "which this platform does not support";
}
// 逐用例级：能按"配置内容是否真的含 control-sockets"进一步收窄
if (!BaseServerTest::unixControlSocketsUsable() &&
    config.find("control-sockets") != std::string::npos) { GTEST_SKIP() << ...; }
```

结果：965 跑 = **918 PASS / 47 SKIP / 0 FAIL**（47 = 45 通道 + 2 config-commit），
壳套件 14/14——SKIP 数可审计、消息写明平台语义，其余用例保持全实跑。

功能侧：如实申报平台不支持（README/notes 明写"unix 命令通道平台性不可用"），
服务器其余功能与 HTTP 控制通道正常；**不伪造 unix 等价通道**。

实例补丁：`archives/k/kea-dhcp6/3.0.3/patches/0007`（探针）、`0008`（组级跳过）、
`0009`（逐用例跳过）。

## 边界

- 独立测试二进制（非 gtest 套件）应改用 meson 约定的 **exit 77 = SKIP**，
  且只对平台类 errno（EPERM/EROFS/EACCES）跳过，其他 errno 仍 FAIL
  （见 [[raul-2.0.0-af-unix-bind-blocked-meson-skip]]）。
- 抽象命名空间（`\0` 前缀）不受此限：需要调用方配合、改变接口语义
  （[[DRAFT-libdsme-0.67.0-ohos-abstract-af-unix-socket]] 的 `@` 前缀约定）。
- 挂载点级例外（`/data/storage/el1/base`）仅在沙箱可达且被测代码允许自定义
  路径时成立；构建期测试通常不可达——不要对"路径名语义"做无声替换。
- 不要往提权方向修（sudo/setcap）：CI 与真机包构建环境都无提权途径，
  hmdfs 拒绝 AF_UNIX bind 是平台设计行为。

## 关键词

`AF_UNIX`, `unix socket`, `bind`, `EPERM`, `hmdfs`, `GTEST_SKIP`, `gtest`,
`meson test skip`, `exit 77`, `control socket`, `control channel`,
`CtrlChannelDhcpv6SrvTest`, `kea`, `dhcp6`, sandbox, `ENAMETOOLONG`, `sockaddr_un`

## 相关条目

- **[[raul-2.0.0-af-unix-bind-blocked-meson-skip]]** —— 同根因，独立二进制
  场景的 exit 77 跳过机制；本条补 gtest 单二进制场景的粒度跳过
- **[[DRAFT-ohos-agent-socket-tmpdir-only-bindable-path]]** —— 挂载点级
  bind 白名单全表（/dev/shm EACCES、唯一例外 /data/storage/el1/base、
  抽象命名空间全通）；gnupg 案例中整包 setup 失败、无法跳过
- **[[DRAFT-libdsme-0.67.0-ohos-abstract-af-unix-socket]]** —— 抽象命名
  空间路线（`@` 前缀约定）的功能侧修复
- **E024** —— 正式文档条目：Unix domain socket bind 受限 → 改用 TCP 回环
  （替代通道方向；kea 的 HTTP 控制通道即此等价面）
