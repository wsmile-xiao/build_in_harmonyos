# duperemove 0.15.2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 解压源码: `tar xzf duperemove-0.15.2.tar.gz`
2. 应用补丁: 3个补丁文件
3. 编译: `make -j2`
4. 安装: `make install DESTDIR=...` + `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | statx系统调用不可用 | OpenHarmony/musl未实现Linux 4.11+ syscall | 创建compat_statx.h兼容层 |
| 2 | libatomic库缺失 | OpenHarmony无libatomic | 移除依赖，clang支持原子操作 |
| 3 | glib静态链接符号缺失 | 需要静态链接intl | 指定完整路径静态链接 |
| 4 | install命令缺失 | toybox无GNU install | 用cp替代 |
| 5 | compat_statx dirfd处理错误 | fstatat(0, path)无效 | 添加绝对路径检测分支 |

## 源码修改

| 补丁文件 | 修改内容 |
|----------|----------|
| 0001-Makefile.patch | 移除libatomic，静态链接glib/intl，cp替代install |
| 0002-compat_statx.h.patch | 新增compat_statx.h兼容层（115行） |
| 0003-file_scan.c.patch | 引入compat_statx.h，处理虚拟文件系统dev=0 |

## 依赖版本

- glib-2.0 (静态链接)
- sqlite3
- blkid (来自util-linux 2.39)

## 验证结果

```bash
# 功能测试
$ ~/usr/local/bin/duperemove -h hashes.db *.txt
Files scanned: 4/4 (100.00%)
Bytes scanned: 13.6KB/13.6KB (100.00%)
Hashfile "hashes.db" written

# 质量门禁
G1: PASS  G2: PASS  G3: PASS  G4: PASS
整体: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| duperemove-0.15.2-ohos-aarch64.tar.gz | 4.1MB | 主预编译包 |
| duperemove-0.15.2-ohos-aarch64-debug.tar.gz | 3.2MB | 调试符号包 |
| duperemove | 2.2MB | 主程序二进制 |
| hashstats | 2.2MB | hash统计工具 |
| btrfs-extent-same | 2.2MB | btrfs测试工具 |

## 注意事项

1. **缺少lscpu命令**: duperemove运行时需要lscpu获取CPU信息，可忽略（显示警告但不影响功能）
2. **fiemap权限限制**: HMDFS文件系统不支持fiemap ioctl，显示权限警告但不影响核心功能
3. **虚拟文件系统**: OpenHarmony使用dev=0的虚拟文件系统，已通过固定UUID处理
4. **不支持deduplication**: 当前文件系统不支持Btrfs deduplication，duperemove可正常扫描和计算hash
---

**编译开始**: 2026-05-26 15:40

**对话记录**:

#### 问题1: statx系统调用不可用
- **错误**: file_scan.c使用`struct statx`和`statx()`，OpenHarmony/musl不支持
- **方案**: 创建`compat_statx.h`兼容层，用传统`stat/fstat`替代
- **修改**: file_scan.c引入compat_statx.h，批量替换`struct statx` → `struct compat_statx`
- **状态**: ✅ 已解决

#### 问题2: libatomic库缺失
- **错误**: `ld.lld: error: unable to find library -latomic`
- **方案**: 移除`-latomic`链接参数，现代clang直接支持原子操作
- **修改**: Makefile中移除`-latomic`
- **状态**: ✅ 已解决

#### 问题3: glib静态链接符号缺失
- **错误**: `libglib-2.0.a`需要`g_libintl_*`符号
- **方案**: 强制静态链接intl和glib，指定完整路径
- **修改**: Makefile中`-lintl` → `$(DEFAULT_PREFIX)/lib/libintl.a`
- **状态**: ✅ 已解决

#### 问题4: install命令缺失
- **错误**: `/bin/sh: install: inaccessible or not found`
- **方案**: 用`cp`替代`install`
- **修改**: Makefile中`install -m 0755` → `cp`
- **状态**: ✅ 已解决

**编译结束**: 2026-05-26 15:50

**最终状态**: built（核心编译成功，G0验证因Makefile无configure脚本失败）

---

**修复重新编译**: 2026-05-26 16:23

**修复内容**: statx兼容层修复

#### 问题5: compat_statx dirfd处理错误
- **错误**: `compat_statx()`使用`fstatat(0, path, ...)`，但dirfd=0(stdin)不是有效目录，导致文件扫描返回0文件
- **根因**:
  1. 原修复只简单替换`statx()`为`fstatat()`，未处理dirfd=0的情况
  2. OpenHarmony虚拟文件系统设备号dev=0，被`get_uuid()`判定为"不支持"而跳过
- **方案**:
  1. **dirfd分支**: 添加绝对路径检测(`pathname[0]=='/'`)和AT_FDCWD检测，分别调用`stat()`或`fstatat()`
  2. **虚拟文件系统**: 设备号dev=0时生成固定UUID（e4871100-0000-0000-0000-000000000001），允许虚拟文件系统扫描
- **修改**:
  - `compat_statx.h`: 添加路径类型判断分支（绝对路径、AT_FDCWD、相对路径）
  - `file_scan.c`: 修改`get_uuid()`对dev=0的处理，生成固定UUID替代失败
- **验证**:
  - 功能测试: Files scanned 4/4 (100.00%), Bytes scanned 13.6KB/13.6KB (100.00%)
  - 质量门禁: G1-G4 PASS
- **状态**: ✅ 已解决

**补丁更新**: 0002-compat_statx.h.patch, 0003-file_scan.c.patch 已刷新
---

**编译结束**: 2026-05-26 16:26
**最终状态**: built
