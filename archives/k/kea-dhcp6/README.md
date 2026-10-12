# kea-dhcp6

ISC Kea 的 **kea-dhcp6**（DHCPv6 服务器），适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

`kea-dhcp6` 是 Kea 提供的 DHCPv6 服务器：按 JSON 配置为客户端分配 IPv6 地址
（IA_NA）与委派前缀（IA_PD），支持地址池、子网、选项（option-def/data）、
租约数据库（memfile/MySQL/PostgreSQL）、动态重配置（SIGHUP）、钩子扩展
（hook libraries）与 unix/HTTP 控制通道；提供 `-t` 配置语法检查、`-W` 构建
配置报告等管理选项。

- 上游项目：ISC Kea 3.0.3（MPL-2.0）
- 源码路径：`src/bin/dhcp6/`（与 Kea 同一源码树，Meson 单工程构建）
- 安装路径：上游 `SBINDIR`（本包按 Conan 约定安装到 `bin/kea-dhcp6`）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.85.0 | 强制；1.90/1.91 制品仓包缺 Kea 实际使用的头文件，须固定版本 |
| log4cplus | 2.2.0.1 | 强制；Kea 日志后端 |
| openssl | 3.5.8.1 | 强制；默认 crypto 后端（`CRYPTO_DEP`） |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） |
| meson | 1.11.0 | 构建工具（tool_requires，须 ≥ 1.10） |

包内同时携带服务器运行期加载的 20 个 Kea 共享库（`readelf -d` NEEDED 闭包，
含物化的 soname 名），因此安装后无需额外的 Kea 运行库即可直接执行。

## OHOS 适配要点

1. **平台名归一化**：Meson 报告 `harmonyos`，Kea 平台分支白名单不含它 →
   顶层 `meson.build` 归一化为 `linux`（补丁 0001，家族）。
2. **UAPI 头冲突**：`linux/socket.h` 与 musl `sys/socket.h` 都定义
   `struct sockaddr_storage` → define-guard 重命名（补丁 0002，家族）。
3. **boost/musl 差异**：定义 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`（工具链注入）。
4. **脚本 execve 限制**：configure 期脚本与 conan 的 meson 包装脚本均经
   sh/解释器执行（补丁 0003/0004 + 配方 `_meson()` 前缀）。
5. **soname 物化**：OHOS 拒绝符号链接，`_materialize_sonames()` 以复制方式
   物化 `libkea-X.so.N`，否则 meson 测试与包内服务器都报
   "Error loading shared library"。
6. **unix 命令通道平台性不可用**：hmdfs 存储拒绝 AF_UNIX 路径名 `bind()`
   （EPERM）；测试用同型 bind 探针判定后跳过 47 例（补丁 0007-0009）。
7. **/tmp 只读**：测试沙箱与 HTTP 控制通道测试路径改用 `TMPDIR`
   （补丁 0006/0010）。

## 上游测试

`src/bin/dhcp6/tests/meson.build` 注册 2 个套件，在 `build()` 内真实执行
（`--timeout-multiplier 4`）：

| 套件 | 用例 | 说明 |
|------|------|------|
| `kea-dhcp6-tests` | 965 跑 / 918 过 / 47 跳 / 0 挂（31 套件） | 配置解析与继承、租约与分配、IA_NA/IA_PD、DUID、iface_mgr、状态机、控制通道等；47 跳为 hmdfs 不支持 AF_UNIX 路径名 bind 的平台性跳过（45 通道 + 2 config-commit） |
| `dhcp6_process_tests.sh` | 14/14 | 真实启动/停止 kea-dhcp6 的进程级套件（信号、日志、pid 文件、syntax check、LFC 定时器等） |

meson 汇总实测：**Ok: 2 / Fail: 0**（0 失败）。

## test_package（消费者视角 + 鸿蒙特有用例）

`conan create` 的 test 阶段真实编译并执行 3 个测试（CMake + `find_package(kea-dhcp6)`）：

| 测试 | 断言 | 内容 |
|------|------|------|
| `test_kea_dhcp6.py` | 16 | 版本输出（`-v`/`-V`）、构建配置报告（`-W`）、`-t` 语法检查三个路径（合法/非法 subnet/缺失文件）、非法选项 `-z` 拒绝与 usage |
| `test_ohos_platform`（**鸿蒙特有**） | 8 | 包内 `bin/kea-dhcp6` 的 OHOS 平台 ABI 特征：ELFCLASS64 / `EM_AARCH64` / `ET_DYN`(PIE)、`DT_NEEDED` 链接 musl `libc.so` 且非 glibc `libc.so.6`、链接 `libc++_shared.so` |
| `test_ohos_runtime`（**鸿蒙特有**） | 6 | OHOS 加载器下的运行时闭包：`DT_NEEDED` 的 Kea 库全部随包分发、20 个 `libkea-*.so*` 全部 `dlopen(RTLD_NOW)` 成功、真实执行 `kea-dhcp6 -v` 输出 `3.0.3` |

鸿蒙特有测试用例 **2 个**，实测 **2/2 通过**。

## 使用

```bash
conan install --requires=kea-dhcp6/3.0.3 -pr:h=<ohos-aarch64 profile>

# 版本 / 构建配置报告
kea-dhcp6 -v
kea-dhcp6 -W

# 配置语法检查
kea-dhcp6 -t /path/to/kea-dhcp6.conf

# 启动服务器（示例最小配置）
cat > kea-dhcp6.conf <<'EOF'
{
  "Dhcp6": {
    "interfaces-config": { "interfaces": [ ] },
    "subnet6": [ ]
  }
}
EOF
kea-dhcp6 -c kea-dhcp6.conf
```
