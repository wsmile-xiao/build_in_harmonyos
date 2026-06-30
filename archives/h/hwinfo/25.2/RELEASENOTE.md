# Release Notes - hwinfo 25.2

## 版本信息
- **版本号**: 25.2
- **发布日期**: 2026-04-29
- **构建平台**: OpenHarmony aarch64
- **编译器**: clang 15

## 主要变更

### 鸿蒙平台适配
- 修复 Makefile 自动生成 version.h 文件失败问题
- 解决 HMDFS 文件系统符号链接限制（使用 cp -a 替代 ln -s）
- 绕过系统缺少 install 命令的问题

### 编译警告处理
- `-Wshift-negative-value`: hddb.c 中宏 DATA_VALUE 的移位操作（保留，代码逻辑正确）
- `-Wgnu-designator`: GNU 旧式字段设计器扩展（保留，符合 GNU 标准）
- `-Wempty-body`: cpu.c 和 floppy.c 中的空语句（保留，代码风格）

## 功能验证

✅ 基本功能测试通过：
- 版本查询: `hwinfo --version` → 输出 `25.2`

## 已知问题

⚠️ 系统限制：
- 系统缺少 GNU install 命令，需要手动安装文件
- HMDFS 文件系统不支持符号链接覆盖（ln -sf）

## 依赖信息

- **编译依赖**: 无外部依赖
- **运行依赖**: 
  - libhd.so.25.2（共享库）
  - Perl（用于 convert_hd 脚本）

## 安装包信息

### 预编译包
- **文件名**: `hwinfo-25.2-ohos-aarch64.tar.gz`
- **大小**: TBD
- **内容**:
  - `/usr/sbin/hwinfo` (4.7M)
  - `/usr/sbin/check_hd` (131K)
  - `/usr/sbin/convert_hd` (68K)
  - `/usr/sbin/getsysinfo` (1.6K)
  - `/usr/sbin/mk_isdnhwdb` (87K)
  - `/usr/lib/libhd.so.25.2` (4.6M)
  - `/usr/lib/libhd.a` (6.6M)
  - `/usr/lib/pkgconfig/hwinfo.pc`
  - `/usr/include/hd.h`
  - `/usr/share/hwinfo/ISDN.CDB.hwdb`

### Debug 包
- **文件名**: `hwinfo-25.2-ohos-aarch64-debug.tar.gz`
- **内容**: 未 strip 的二进制文件和 .o 目标文件

## 安全信息

- **ELF 签名**: 已签名（通过 ohc-run.py sign-elf）
- **权限**: 755 (可执行文件)
- **所有权**: root:root

## 测试结果

### make check
- **状态**: 未执行（项目无测试套）
- **原因**: hwinfo 项目没有标准的 make check 目标

### 功能测试
- ✅ 版本查询
- ⚠️ 硬件扫描（需要实际硬件环境验证）

## 文档参考

- README.md - 项目介绍和使用说明
- PROGRESS.md - 编译过程详细记录
- quality-report.md - 质量门禁报告

---

**构建者**: OpenHarmony Compile Agent  
**构建日期**: 2026-04-29