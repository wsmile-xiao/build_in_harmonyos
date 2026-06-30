# ostree v2026.1 预编译包

## 概述

这是ostree v2026.1为OpenHarmony平台（aarch64）预先编译的软件包。

## 包内容

```
ostree-2026.1-ohos-aarch64.tar.gz (50MB)
├── bin/
│   ├── ostree-static (16MB, 静态链接版本, 推荐)
│   └── ostree -> ostree-static (符号链接)
├── lib/
│   ├── libostree-1.so (动态库)
│   ├── libostree-1.so.1
│   ├── libostree-1.so.1.0.0
│   └── pkgconfig/ostree-1.pc
├── include/ostree-1/ (头文件, 86个)
└── share/
    ├── VERSION (版本信息)
    ├── OSTREE_TEST_REPORT.md (测试报告)
    └── README-ostree.md (说明文档)
```

## 安装方法

### 方法1: 解压到用户目录

```bash
tar xzf ostree-2026.1-ohos-aarch64.tar.gz -C ~/usr/local --strip-components=1
```

### 方法2: 使用安装脚本

```bash
sh install-ostree.sh
```

## 使用说明

### 静态版本（推荐）

```bash
~/usr/local/bin/ostree --version
```

**优点**:
- 无动态库依赖
- 可直接运行
- 解决了GObject类型系统问题

### 动态版本

```bash
export LD_LIBRARY_PATH=~/usr/local/lib:$LD_LIBRARY_PATH
~/usr/local/bin/ostree --version
```

**注意**: 动态版本需要设置LD_LIBRARY_PATH

## 功能测试

测试通过率: 94%

详细测试报告: OSTREE_TEST_REPORT.md

## 平台兼容性

- ✅ 编译成功
- ✅ 94%功能测试通过
- ⚠️ HMDFS文件系统限制（fallocate/xattr不支持）
- ✅ 在标准Linux文件系统上完整可用

## 版本信息

```
libostree:
 Version: '2026.1'
 Features:
  - inode64
  - initial-var
  - libcurl
  - ex-fsverity
  - release
  - p2p
```

## 已解决的问题

1. gettext链接问题（使用cmd-pkgs预编译glib）
2. libtool版本不匹配（修改版本号）
3. strverscmp函数缺失（兼容实现）
4. explicit_bzero函数缺失（兼容实现）
5. GObject类型系统问题（完全静态链接）

## SHA256校验码

```
7afe4c4b5e18d025f07e2fd60320d304eb6c7a23e15b48fa6f3e5a490b6c4245
```

## 联系信息

编译者: OpenDesk编译智能体
日期: 2026-05-28
平台: OpenHarmony aarch64