# lft 3.93 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
source .build-context-lft-3.93
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX --with-pcap=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别 HarmonyOS | 2006 版过旧，不含 ohos 检测 | 替换为 2021 版 + 手动添加 aarch64-unknown-linux-ohos 检测 |
| 2 | musl libc 下 `_res` (struct __res_state) 全局符号不存在 | musl 不支持 res_state 全局变量 | 用 `#ifdef __OHOS__` 守卫替代（R8 铁律） |
| 3 | HMDFS 文件系统 umask 077 创建目录权限 drwx--S--- | configure/config.guess 中 umask 077 导致 HMDFS 权限错误 | 全局搜索替换 umask 077 → umask 022（含 configure、config.guess、config/config.guess） |
| 4 | /tmp 只读无法写入 | HarmonyOS /tmp 是只读分区（E002） | 设置 TMPDIR=/storage/Users/currentUser/tmp |
| 5 | configure 中 config.status heredoc 嵌入 umask 077 | autotools 生成的临时目录创建代码使用 umask 077 | 替换为 umask 022，并在全局添加 `umask 022` 保护 |
| 6 | manifest.yaml 缺少 build_system 字段 | G4 门禁检查要求顶层 build_system 字段 | 在 manifest.yaml 顶层添加 `build_system: autotools` |
| 7 | 软件级目录缺少 README.md | G4 门禁要求 archives/l/lft/ 下必须有 README.md | 创建中文 README.md |
| 8 | configure_options 含 --host 参数 | 违反 R15 铁律（native 编译禁止 --host） | 移除 `--host=aarch64-unknown-linux-ohos`，依赖 config.guess 自动检测 |

## 源码修改

共 8 个补丁文件，覆盖 8 个源文件修改：

| 补丁 | 修改文件 | 类型 | 说明 |
|------|---------|------|------|
| 0001-acconfig.h.in.patch | acconfig.h.in | config 生成文件 | 添加 __OHOS__ 守卫的配置项 |
| 0002-config.guess.patch | config.guess | 平台检测 | 替换 2021 版 + ohos 检测 + umask 077→022 |
| 0003-config.sub.patch | config.sub | 平台检测 | 替换 2021 版 + ohos-linux 映射 |
| 0004-config-config.guess.patch | config/config.guess | 平台检测 | 替换 + ohos 检测 + umask 077→022 |
| 0005-config-config.sub.patch | config/config.sub | 平台检测 | 替换 + ohos-linux 映射 |
| 0006-configure.patch | configure | config 修复 | umask 077→022 + 全局 umask 022 保护 + TMPDIR 适配 |
| 0007-configure.ac.patch | configure.ac | config 源文件 | 对应 configure 的修改源文件 |
| 0008-lft.c.patch | lft.c | 源码修复 | `#ifdef __OHOS__` 守卫替代 _res（R8 铁律） |

## 依赖版本

- libpcap 1.10.5（已安装预编译包）

## 验证结果（真实执行）

### lft 版本验证
```
Layer Four Traceroute (LFT) - version 3.93 (09/2025)
    + Linux platform
    + aarch64-unknown-linux-ohos
```

### whob 版本验证
```
WhoB - version 3.92
```

### G0 干净构建验证
原始 tarball 解压 → 8个补丁应用 → configure → make → install，全部通过。

### G1-G4 质量门禁
G1 ✅ | G2 ✅ | G3 ✅ | G4 ✅

### 限制说明
- lft traceroute 功能需要 CAP_NET_RAW 权限（正常，网络诊断工具需特权）
- 二进制使用 `-v` 查看版本（不支持 `--version`）
- 运行需要 LD_LIBRARY_PATH 指向 libpcap.so

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lft-3.93-ohos-aarch64.tar.gz | 612KB | 预编译包（含 bin/lft、bin/whob、lib/external/libpcap.so） |
| lft-3.93-ohos-aarch64-debug.tar.gz | 84KB | 调试符号包 |

## 注意事项

- umask 077→022 修复需全局搜索（configure + config.guess + config/config.guess 三处均已修复）
- lft.c 的 `#ifdef __OHOS__` 守卫遵循 R8 铁律
- 依赖 libpcap 需先安装预编译包
- 本编译为打回重做（G0 umask 问题 + G4 档案完整性问题已修复）

---

**编译结束**: 2026-06-10 10:05
**最终状态**: published
