# libedit 20240808 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-17
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 1. 下载源码并解压
tar -xzf libedit-20240808-3.1.tar.gz
cd libedit-20240808-3.1

# 2. 应用补丁
patch -p1 < patches/0003-config.guess.patch
patch -p1 < patches/0004-config.sub.patch
patch -p1 < patches/0010-configure-umask.patch
# ... 其余补丁同理

# 3. 配置（仅 --prefix，R1 参数最少化）
./configure --prefix=$HOME/usr/local

# 4. 编译
make -j$(nproc)

# 5. 安装
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS 文件系统限制，config.status 无法创建临时子目录 | HMDFS umask 077 导致目录权限不足 | 应用 0010-configure-umask.patch 将 umask 从 077 改为 022 |
| 2 | config.guess 不识别 HarmonyOS 平台 | 上游 autotools 版本未包含 OHOS 支持 | 应用 0003-config.guess.patch 添加 HarmonyOS 系统检测 |
| 3 | config.sub 不识别 ohos triplet | 同上 | 应用 0004-config.sub.patch 添加 ohos-linux triplet 支持 |
| 4 | build-aux 脚本 shebang 不兼容 | autotools 版本差异 | 应用 0002/0006/0007/0008 补丁修复 compile/depcomp/install-sh/missing |
| 5 | 缺少 termcap.h 头文件 | HarmonyOS 系统无 ncurses/termcap 头文件 | 应用 0009-termcap.h.patch 提供最小 termcap.h 声明 |

## 源码修改

- `aclocal.m4`: 替换为兼容 HarmonyOS 的版本
- `compile`: 修复 shebang 和脚本版本兼容性
- `config.guess`: 添加 HarmonyOS 系统检测（`__OHOS__` 宏 + HarmonyOS uname 匹配）
- `config.sub`: 添加 ohos-linux triplet 支持
- `configure` (0005): automake 版本兼容性修复
- `configure` (0010): 修复 HMDFS umask 077→022 权限问题
- `depcomp`/`install-sh`/`missing`: 修复 shebang 兼容性
- `termcap.h` (新增): HarmonyOS 最小 termcap.h 函数声明

## 依赖版本

无外部依赖，libedit 是自包含的 BSD 行编辑库。使用系统 libtinfo (libtinfo.so.6 at /usr/lib/)。

## 验证结果

```bash
# 检查安装产物
ls -la $HOME/usr/local/lib/libedit*
# libedit.a / libedit.so

# 检查头文件
ls $HOME/usr/local/include/histedit.h
```

## 注意事项

- libedit 不是系统同名库，默认动态链接，不需要 R26 静态隔离
- 补丁 0001-aclocal.m4.patch 较大（9132行），为整体替换 aclocal.m4 生成文件
- 0005-configure.patch 修复 automake 兼容性，0010-configure-umask.patch 修复 umask 权限
---

**编译结束**: 2026-08-10 06:10
**最终状态**: built
