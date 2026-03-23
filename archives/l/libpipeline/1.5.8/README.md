# libpipeline 1.5.8 鸿蒙系统编译指南

## 一、概述

libpipeline 是一个用于方便构建管道的 C 库，提供对管道操作的抽象封装。它是 man-db 的必需依赖库。

## 二、软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | libpipeline |
| 版本 | 1.5.8 |
| 官方网站 | https://www.nongnu.org/libpipeline/ |
| 下载地址 | https://download.savannah.nongnu.org/releases/libpipeline/libpipeline-1.5.8.tar.gz |
| 构建系统 | Autotools (configure) |

## 三、鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel |
| 架构 | aarch64 |
| 编译器 | Clang 15.0.4 |
| C 库 | musl libc |
| 工具链 | LLVM (ld.lld) |

## 四、编译步骤

### 4.1 下载和解压

```bash
cd $HOME/tmp
curl -LO https://download.savannah.nongnu.org/releases/libpipeline/libpipeline-1.5.8.tar.gz
tar -xzf libpipeline-1.5.8.tar.gz
cd libpipeline-1.5.8
```

### 4.2 应用 HarmonyOS 补丁

```bash
# 对 config.guess 和 config.sub 应用标准 HarmonyOS 补丁
# 详见下方补丁说明
```

### 4.3 配置

```bash
export PATH=$HOME/usr/local/bin:$PATH
export CC=clang
export CFLAGS="-fPIC -O2"

./configure --prefix=$HOME/usr/local
```

### 4.4 编译和安装

```bash
make -j1
make install
```

### 4.5 修复共享库软链接

```bash
cd $HOME/usr/local/lib
cp libpipeline.so.1.5.8 libpipeline.so
cp libpipeline.so.1.5.8 libpipeline.so.1
```

> **注意**: HarmonyOS SELinux 限制导致 `ln -sf` 创建的软链接无法被动态链接器跟随，必须使用 `cp` 代替。

## 五、补丁说明

### 5.1 HarmonyOS 系统检测补丁 (config.guess/config.sub)

与所有 autotools 项目相同的 HarmonyOS 补丁模板。

#### config.guess — 两处修改

**修改 1**: LIBC 检测中添加 `__OHOS__` 判断（位于 `Linux|GNU|GNU/*` case 内）

```c
#if defined(__OHOS__)
LIBC=ohos
#elif defined(__ANDROID__)
    LIBC=android
```

**修改 2**: 添加 HarmonyOS 系统 case（位于 `*:Minix:*:*` 之后）

```bash
*:HarmonyOS:*:*)
    GUESS=$UNAME_MACHINE-unknown-linux-ohos
    ;;
```

#### config.sub — 三处修改

1. **maybe_os** 添加 `ohos-linux` 匹配，产生 `linux-ohos` 三元组
2. **OS 允许列表** 加 `ohos*`
3. **kernel-os 验证** 加 `linux-ohos*`（linux kernel + ohos os 组合）

## 六、安装结果

### 6.1 安装的文件

```
$HOME/usr/local/
├── include/
│   └── pipeline.h           # 头文件
└── lib/
    ├── libpipeline.a        # 静态库
    ├── libpipeline.so       # 共享库 (cp 副本)
    ├── libpipeline.so.1     # 共享库 (cp 副本)
    ├── libpipeline.so.1.5.8 # 共享库 (实际文件)
    └── pkgconfig/
        └── libpipeline.pc   # pkg-config 文件
```

## 七、遇到的问题

### 问题 1: 共享库软链接失效

**现象**: 安装后程序无法加载 `libpipeline.so`。

**原因**: HarmonyOS SELinux 限制导致 `ln -sf` 创建的符号链接无法被动态链接器跟随。

**解决方案**: 使用 `cp` 代替 `ln -s`：
```bash
cp libpipeline.so.1.5.8 libpipeline.so
cp libpipeline.so.1.5.8 libpipeline.so.1
```

## 八、经验总结

### 8.1 关键经验

1. **标准 autotools 流程**: libpipeline 编译较简单，无特殊依赖，标准的 configure/make/make install 即可
2. **软链接替代**: SELinux 限制下需用 cp 代替 ln -s 安装 .so 文件
3. **作为依赖库的独立性**: 依赖软件应作为独立项目单独记录归档

### 8.2 依赖关系

| 被依赖项目 | 用途 |
|----------|------|
| man-db | 核心依赖，提供管道构建抽象 |

## 九、参考资料

- libpipeline 官方网站: https://www.nongnu.org/libpipeline/
- man-db 编译档案: archives/m/man-db/2.13.1/

---

*文档生成时间: 2026-03-23*
