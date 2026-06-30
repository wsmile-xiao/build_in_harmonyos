# libdsk 1.4.2 — OpenHarmony 预编译包说明

LibDsk 是一个通用软盘和磁盘镜像访问库，支持多种磁盘镜像格式（DSK、EDSK、IMD、RAW、SIMH、JV3 等）。

## 平台信息

- 目标架构: aarch64 (ARM64)
- 操作系统: OpenHarmony (aarch64-unknown-linux-ohos)
- 编译器: clang/clang++
- 构建日期: 2026-06-11

## 安装方法

```bash
tar xzf libdsk-1.4.2-ohos-aarch64.tar.gz -C <目标路径>
```

## 包含内容

### 可执行文件（8个）
- `dsktrans` — 磁盘镜像转换工具
- `dskform` — 磁盘镜像格式化工具
- `dskid` — 磁盘镜像识别工具
- `dskdump` — 磁盘镜像内容输出工具
- `dskscan` — 磁盘镜像扫描工具
- `dskutil` — 磁盘镜像交互工具
- `md3serial` — MicroDesign 序列号工具
- `apriboot` — Apricot 引导扇区工具

### 共享库
- `libdsk.so.3.3.13` (→ libdsk.so.3 → libdsk.so)
- `libdsk.a` (静态库)

### 头文件
- `libdsk.h` — 公共 API 头文件

### 手册页
- man1: dskform.1, dsktrans.1, dskid.1, md3serial.1, dskscan.1, dskdump.1, dskutil.1, apriboot.1
- man5: libdskrc.5

## 版本验证

```bash
dsktrans --version   # 输出: libdsk version 1.4.2
```

## 使用示例

```bash
# 格式化一个 720KB DSK 镜像
dskform -format pcw720 myfile.dsk

# 转换 DSK 到 RAW 格式
dsktrans -itype dsk -otype raw myfile.dsk myfile.raw

# 识别镜像几何参数
dskid -type dsk myfile.dsk

# 扫描镜像内容
dskscan -type dsk myfile.dsk
```

## 已知限制

- 需要物理软盘设备的测试（check2/check3）在 OpenHarmony 上无法执行
- config.status 的 umask 077 修补需在每次 configure 后手动执行
- lyx 文档生成步骤不可用（无 lyx 工具）

## 许可证

GNU Library General Public License v2