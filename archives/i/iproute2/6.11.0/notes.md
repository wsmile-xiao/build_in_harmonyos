# iproute2 6.11.0 适配笔记

## 编译环境
- 构建系统: makefile（iproute2 自带 configure 特性探测 + GNU make）
- 编译日期: 2026-07-16
- 编译器: OHOS clang/clang++ 15.0.4（`--target=aarch64-linux-ohos`）
- sysroot: OHOS Native SDK（HarmonyOS 6.0, aarch64, musl libc）
- 状态: built（交叉编译产出已核实为 aarch64 静态 ELF；conan create/L1 运行验证待 CI 或模拟器执行）

## 编译步骤
1. `./configure` —— iproute2 自带脚本，探测内核特性生成 `config.mk`（bison/flex 为必需构建工具）。
2. `make SUBDIRS="lib ip tc bridge misc genl" CC=<clang> CCOPTS="-O2 -pipe -include <src>/include/ohos_compat.h -Wno-implicit-function-declaration -Wno-int-conversion -D__UAPI_DEF_IN6_ADDR=0 ...(共 7 项 UAPI guard)" LDFLAGS="-static" -j1`
3. 补丁 `0001-ohos-musl-compat.patch` 新增 `include/ohos_compat.h`，经 `-include`（绝对路径，因各子目录 ip/、tc/… 内编译，相对路径无法命中）强制最先引入。
4. 安装：`make SUBDIRS=... install DESTDIR=<pkg> PREFIX=/ SBINDIR=/bin LIBDIR=/lib`，二进制落到 `<pkg>/bin`。

> `SUBDIRS` 覆盖默认的 `lib ip tc bridge misc netem genl man`：剔除 `netem`（含 host 工具 maketable/normal，不能用 target 交叉标志编）与 `tipc/devlink/rdma/dcb`（依赖 libmnl，OHOS sysroot 未含）。conanfile.py 的 build()/package() 已固化上述做法。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ipseg6.c`: implicit declaration of `getpass` / 动态链接 `undefined symbol: getpass` | OHOS libc.so 未导出 getpass（动态库符号裁剪）；头文件也无声明 | 补声明 + **静态链接**：静态 `libc.a` 含 `T getpass` 真实现，`-static` 即解析（见 E215） |
| 2 | `bridge`/`ss` 等: `redefinition of 'struct in6_addr'` / 后续 `incomplete type` | 内核 UAPI 头（linux/in6.h 等）与 musl `netinet/in.h` 结构体重定义；musl 无 glibc 的 libc-compat.h 联动机制 | 命令行 `-D__UAPI_DEF_IN6_ADDR=0` 等让内核头让位 + compat 头先 `#include <netinet/in.h>` 让 musl 先定义（见 E216） |
| 3 | `tipc/devlink/rdma/dcb`: `libmnl/libmnl.h not found` | 这四个工具依赖外部库 libmnl，OHOS sysroot 未含 | 依赖链边界：核心工具集不受影响；这些工具待 libmnl 先适配（非本库阻塞） |

## getpass 铁证（对现有知识库 E093 的实证补充，详见 E215）

| 位置 | getpass 符号 | 结论 |
|------|-------------|------|
| `libc.so`（72 KB 动态库） | 无 | 动态链接失败 |
| `libc.a`（11 MB 静态库） | `getpass.o: 0000... T getpass` | **有完整真实现** |
| 产出 `ip` 二进制 | `...2972e0 T getpass` | 静态链接已并入、成功解析 |

→ E093 断言"musl 不实现 getpass、⛔ 不要声明"在 **OHOS 静态编译（R26）** 场景下不成立。
补声明 + `-static` 用的是 libc 自带的**真** getpass（关闭终端回显、安全），优于 E093 现方案（自写 fgets 替代、不关回显）。

## 补丁
- `patches/0001-ohos-musl-compat.patch` — 新增 `include/ohos_compat.h`（getpass 声明 + musl 网络头前置）。

## 依赖版本
- 无第三方 Conan 依赖（核心工具集）。构建工具：bison、flex、gcc（host 侧）。

## 验证结果
```
$ file ip/ip
ip/ip: ELF 64-bit LSB executable, ARM aarch64, statically linked
# 核心 8 工具均为 aarch64 statically linked：
ip tc bridge ss lnstat nstat rtacct genl
```

## 运行期功能验证（R40：系统底层 netlink 库，需人工确认适配完整性）

iproute2 通过 netlink 与内核网络栈交互，属 R40「系统底层：procfs/sysfs/netlink/dl」范畴，
**需人工确认适配完整性**。当前验证状态：

| 层级 | 内容 | 状态 |
|------|------|------|
| 构建 | 交叉编译产出 aarch64 静态 ELF（核心 8 工具） | ✅ 已验证 |
| 版本 | `ip -V` 输出 `iproute2-6.11.0` | ✅ 已在 CI build #6566（aarch64, results:0）验证 |
| netlink 只读查询 | `ip link/addr/route show`、`ip -s link`、`ip neigh/rule show`、`bridge link`、`tc qdisc`、`ss -s`/`ss -tan` | ⏳ 待人工确认 |
| netlink 写操作 | `ip link add/set`、`ip addr add`、`ip route add`（需 root/CAP_NET_ADMIN） | ⏳ 待人工确认 |

`test_package/test.sh` 已扩展覆盖上述只读 netlink 查询（RTM_GETLINK/GETADDR/GETROUTE/GETNEIGH、sock_diag），
在真实 aarch64 内核上运行即可验证 netlink 接口可用性与适配完整性。

**为何本地未能完成功能验证**（两种 OHOS 环境均实测尝试，均受客观限制）：
1. **DevEco PC 模拟器**：实测为 **x86_64**（`uname -m`），而交付物为 aarch64 静态 ELF，模拟器无法执行（报 `not executable: 64-bit ELF file`）。
2. **鸿蒙手机真机**：为 **aarch64**（鸿蒙内核 1.12.0），架构匹配，`ip/tc/bridge/ss` 已成功推送至 `/data/local/tmp` 并经 `file` 确认为 arm64 static ELF；但**消费机 SELinux（enforcing，非 root）禁止 `sh` 域执行 `data_local_tmp` 类型文件**，`./ip -V` 即返回 `Permission denied`，`chcon` 重打标签亦因无权限失败。属平台安全策略限制，非适配缺陷。

因此 netlink 运行期功能验证需在 **root/eng 版 aarch64 设备** 或 **官方 aarch64 CI 环境** 执行 `test.sh` 后回填结果。

**人工确认步骤（aarch64 环境）**：
1. 安装包后进入 conanrun 环境，执行 `bash test_package/test.sh`；
2. 确认 `ip link show` / `ip addr show` 列出接口、`ss -s` 输出套接字汇总（证明 netlink 往返正常）；
3. 通过后将上表 ⏳ 改为 ✅，并在此处附实际输出片段。

## 注意事项
- `netem` 目录含 host 侧构建工具（maketable/normal），由 host gcc 编译，不应被传入 target 的 compat header；
  CI 若从顶层 `make all` 需注意 host/target 编译器分离，或单独指定 SUBDIRS，避免 host 工具误用交叉标志。
- 运行期验证：`ip -V` 已在 CI build #6566（aarch64）通过；netlink 功能验证（`ip link/addr show` 等）见上节「运行期功能验证（R40）」，需 aarch64 真机运行 `test_package/test.sh`。
