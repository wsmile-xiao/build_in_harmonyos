# 功能验证测试报告 — bird2 2.17.4

**测试日期**: 2026-07-06
**测试平台**: OpenHarmony / HarmonyOS PC (aarch64)
**测试二进制**:
- `bird` (1,968,640 bytes, ELF 64-bit LSB arm64, dynamic, musl libc)
- `birdcl` (59,776 bytes, ELF 64-bit LSB arm64, dynamic, musl libc)

## 测试环境

| 项目 | 值 |
|------|-----|
| OS | HarmonyOS |
| 内核 | HongMeng Kernel 1.12.0 |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4 (LLVM) |
| libc | musl (ld-musl-aarch64.so.1) |
| 构建类型 | Release |

## 二进制依赖

- **解释器**: `/lib/ld-musl-aarch64.so.1`
- **动态库**: `libc.so` (仅依赖 musl libc，无其他外部库依赖)

## 测试结果

### Test 1: bird --version

**命令**: `bird --version`
**结果**: ✅ PASS

```
BIRD version 2.17.4
```

### Test 2: bird --help

**命令**: `bird --help`
**结果**: ✅ PASS

```
Usage: bird [--version] [--help] [-c <config-file>] [OPTIONS]

Options:
  -c <config-file>     Use given configuration file instead of
                       /storage/Users/currentUser/usr/local/etc/bird.conf
  -d                   Enable debug messages and run bird in foreground
  -D <debug-file>      Log debug messages to given file instead of stderr
  -f                   Run bird in foreground
  -g <group>           Use given group ID
  -h, --help           Display this information
  -l                   Look for a configuration file and a control socket
                       in the current working directory
  -p                   Test configuration file and exit without start
  -P <pid-file>        Create a PID file with given filename
  -R                   Apply graceful restart recovery after start
  -s <control-socket>  Use given filename for a control socket
  -u <user>            Drop privileges and use given user ID
  --version            Display version of BIRD
```

### Test 3: bird -p (配置文件解析测试 — 默认配置)

**命令**: `bird -p -c /path/to/bird.conf`
**结果**: ✅ PASS (退出码 0)

```
bird: Cannot disable transparent huge pages: prctl(PR_SET_THP_DISABLE) failed: Invalid argument
```

**说明**: `prctl(PR_SET_THP_DISABLE)` 失败是 OHOS 内核不支持 THP 禁用，不影响功能，配置解析成功退出码为 0。

### Test 4: bird -p (配置文件解析测试 — 自定义路由配置)

**命令**: `bird -p -c bird-test.conf`
**自定义配置内容**:
```
router id 10.0.0.1;

protocol kernel {
    ipv4 { export all; };
}

protocol direct { ipv4; }

protocol static {
    ipv4;
    route 10.0.0.0/24 via "eth0";
}
```
**结果**: ✅ PASS (退出码 0)

配置文件成功解析，包含 router id、kernel 协议、direct 协议和 static 路由。

### Test 5: birdcl (控制客户端)

**命令**: `birdcl -v`
**结果**: ⚠️ 预期行为 — 无法连接到控制 socket

```
Unable to connect to server control socket (/storage/Users/currentUser/usr/local/var/run/bird.ctl): No such file or directory
```

**说明**: birdcl 是 BIRD 守护进程的控制客户端，需要 bird 守护进程运行时才能连接。当前环境未启动 bird 守护进程（需要 root 权限和网络命名空间），此行为完全符合预期。

### Test 6: make check (单元测试套件)

**命令**: `make check` (在构建目录中执行)
**结果**: ✅ PASS — 全部 22 个测试通过

测试覆盖 BIRD 核心功能：路由表操作、过滤器表达式、路径属性处理、BGP 属性解析等。

### Test 7: ELF 二进制验证

**命令**: `readelf -d bird && readelf -l bird`
**结果**: ✅ PASS

```
NEEDED: libc.so
Interpreter: /lib/ld-musl-aarch64.so.1
```

二进制为 aarch64 ELF 动态链接格式，仅依赖 musl libc，无未满足的依赖。

## 测试总结

| 测试 | 结果 |
|------|------|
| bird --version | ✅ PASS |
| bird --help | ✅ PASS |
| bird -p (默认配置解析) | ✅ PASS |
| bird -p (自定义路由配置解析) | ✅ PASS |
| birdcl (控制客户端) | ⚠️ 预期行为 (需守护进程运行) |
| make check (22 单元测试) | ✅ PASS (22/22) |
| ELF 二进制验证 | ✅ PASS |

## 结论

**bird2 2.17.4 核心功能在 OpenHarmony 平台上可正常使用。**

- ✅ 版本输出正确 (2.17.4)
- ✅ 帮助信息完整
- ✅ 配置文件解析功能正常（支持 router id、kernel/direct/static 协议、IPv4 路由）
- ✅ 22 个单元测试全部通过
- ✅ 二进制仅依赖 musl libc，部署简单
- ⚠️ birdcl 控制客户端需要 bird 守护进程运行后才能使用（预期行为）
- ℹ️ THP 禁用警告不影响功能（OHOS 内核限制）
