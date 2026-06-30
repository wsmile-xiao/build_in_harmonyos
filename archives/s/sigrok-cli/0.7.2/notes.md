# sigrok-cli 0.7.2 编译笔记

## 编译环境

- 平台: HarmonyOS (aarch64-unknown-linux-ohos)
- 编译器: clang 15.0.4
- 构建系统: autotools

## 依赖项

### 已安装依赖

| 依赖 | 版本 | 安装路径 |
|------|------|----------|
| libsigrok | 0.5.2 | ~/usr/local |
| glib-2.0 | 2.88.0 | 系统自带 |

### 可选依赖（未安装）

- libsigrokdecode >= 0.5.0（协议解码功能，非必需）

## 编译过程

### 1. 源码准备

```bash
# 源码已存在于归档目录
ls ~/archives/s/sigrok-cli/0.7.2/sigrok-cli-0.7.2/
```

### 2. 平台识别修复

config.guess 和 config.sub 已包含 HarmonyOS 平台识别支持（之前的子任务已修复）。

### 3. 环境设置

```bash
export TMPDIR=/data/storage/el2/base/cache
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
```

### 4. 依赖宏文件

```bash
# pkg.m4 缺失，从网络下载
cd m4/
wget -O pkg.m4 "https://ghfast.top/https://raw.githubusercontent.com/pkgconf/pkgconf/master/pkg.m4"
```

### 5. 配置和编译

```bash
autoreconf -fi
./configure --prefix=/storage/Users/currentUser/usr/local
make -j2
```

### 6. 测试安装

```bash
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-sigrok-cli-0.7.2
```

## 编译结果

- 二进制文件: sigrok-cli (199KB)
- 功能: 命令行信号分析工具
- 依赖: libsigrok.so, libglib-2.0.so

## 遇到的问题

### 问题1: pkg.m4 缺失

**症状**: autoreconf 报错 "PKG_PROG_PKG_CONFIG is m4_require'd but not m4_defun'd"

**解决方案**: 从 pkgconf 项目下载 pkg.m4 文件到 m4/ 目录

## 验证测试

待预编译包制作完成后验证。

---

**编译开始**: 2026-06-08 17:20
**编译结束**: 2026-06-08 17:28
**最终状态**: 成功

## 运行时问题

### 动态链接问题

**症状**: sigrok-cli无法运行，报错找不到共享库（libglib-2.0.so.0等）

**原因**: HarmonyOS使用musl libc动态链接器，LD_LIBRARY_PATH环境变量可能无法正常工作。

**解决方案**: 
1. 预编译包包含所有依赖库（libsigrok、glib系列）
2. 用户需要将lib/external目录添加到搜索路径，或使用install脚本设置正确的环境

### 预编译包内容

预编译包sigrok-cli-0.7.2-ohos-aarch64.tar.gz包含：
- bin/sigrok-cli (82KB)
- lib/external/ 所有依赖库:
  - libsigrok.so.4.1.1 (942KB)
  - libglib-2.0.so.0.7600.0 (1.1MB)
  - libgio-2.0.so.0.7600.0 (1.7MB)
  - libgobject-2.0.so.0.7600.0 (415KB)
  - libgmodule-2.0.so.0.7600.0 (18KB)
  - libintl.so.8 (10KB)
  - libpcre2-8.so.0 (407KB)

---

**打包完成**: 2026-06-08 17:37
