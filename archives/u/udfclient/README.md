# udfclient — UDF 文件系统工具集

## 软件简介

udfclient（UDFtoolkit）是 Reinoud Zandijk 开发的 UDF（ECMA-167 / ISO 13346）文件系统工具集，
用于创建、检查和读写 UDF 光盘与镜像文件。它是自包含的 C 工具集，无第三方库依赖。

**主要工具**:
- `udfclient`: 交互式 UDF 客户端（`ls`/`cd`/`get`/`put`/`mkdir`/`rm`/`sync` 等命令）
- `udfdump`: UDF 结构转储器（顺序扫描描述符 / 挂载卷集 / 导出目录树）
- `newfs_udf`: 格式化 / 创建 UDF 文件系统（支持真实光盘与镜像文件）
- `cd_sessions` / `cd_disect` / `mmc_format`: CD/MMC 介质层工具（SCSI 后端）

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 0.8.21 | built ✅ | 2026-09-27 | 4 |

## 使用方法

```bash
# 查看用法
udfdump -h
newfs_udf -h

# 在镜像文件上创建 UDF 文件系统 (-b 扇区字节数, -s 扇区数量)
newfs_udf -L MYVOL -b 2048 -s 8192 myimg.udf

# 顺序扫描镜像中的 UDF 描述符
udfdump -S myimg.udf

# 挂载镜像, 输出卷集信息与目录树
udfdump -b 2048 -t myimg.udf

# 交互式挂载 (只读)
udfclient -b 2048 myimg.udf
```

> 文件型镜像需要显式 `-b 2048`（工具默认按光盘介质推断扇区大小）。

## 平台适配说明

### 鸿蒙系统适配

**编译补丁**（4 个）:
1. `0001-Makefile.in.patch` — BSD make 的 `$(.TARGET)` 规则改为 GNU make 静态模式规则
   （上游 Makefile.in 面向 bmake/pmake，Conan/CI 使用 GNU make）
2. `0002-config.guess.patch` — 增加 HarmonyOS 识别（`uname -s` = HarmonyOS →
   `aarch64-unknown-linux-ohos`），否则 configure 报 `cannot guess build type`（E007）
3. `0003-config.sub.patch` — 接受 `linux-ohos` 内核-系统对，使 OHOS Conan autotools
   工具链的 `--host/--build` 三元组可用（E205）
4. `0004-configure.patch` — 移除 config.status 临时目录创建中的 `umask 077`
   （HMDFS 强制目录 setgid，`drwx--S---` 目录属主亦不可写，E114）

**编译依赖**: 无第三方依赖（仅 libc/pthread；Linux SCSI 后端使用 OHOS SDK 自带
`scsi/sg.h`，因此 `cd_disect`/`mmc_format` 也会构建）。

**测试**: 上游无自动化测试（无 `tests/` 目录、Makefile.in 无 `check` 目标）；
补充消费者测试 `test_package/test.sh`：创建 UDF 镜像 → 描述符顺序扫描 → 挂载卷集/目录树
→ 只读挂载列出文件集 → 缺失镜像负向控制（13 项断言）。
