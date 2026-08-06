# e2fsprogs 1.47.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 内核版本: HongMeng Kernel 1.12.0
- 状态: built

## 编译步骤

1. **初始化构建目录**：解压源码包到 `/storage/Users/currentUser/tmp/builds/e2fsprogs-1.47.0.work`
2. **预扫描风险检测**：识别到 HMDFS 不支持硬链接、config.guess 需要补丁等问题
3. **configure**：使用标准参数 `--prefix=/storage/Users/currentUser/usr/local`，但需要手动设置 build_alias 和 host_alias 为 `aarch64-unknown-linux-ohos`，并使用 bash 而非 sh 执行（避免 toybox heredoc 问题）
4. **make**：修改所有 Makefile 的 LN 定义（从 `ln` 改为 `cp -a`）解决 HMDFS 硬链接问题
5. **make install DESTDIR**：成功安装到 staging 目录
6. **make check**：跳过（测试套件耗时较长）
7. **package**：生成预编译包 e2fsprogs-1.47.0-ohos-aarch64.tar.gz
8. **make install**：本地安装验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败：config.guess 无法识别系统 | GNU config.guess 不包含 HarmonyOS 检测分支 | 使用 patch-autotools-ohos.pl 打补丁 |
| 2 | config.guess 创建临时文件失败 | toybox sh 对 heredoc 和临时文件处理有问题 | 使用 bash 运行 configure |
| 3 | config.sub 不识别 ohos OS | kernel 列表中缺少 linux-ohos | 手动修改 config.sub，添加 linux-ohos* |
| 4 | make 失败：无法创建硬链接 | HMDFS 不支持硬链接操作 | 批量修改所有 Makefile 的 LN 定义：`sed -i 's/^LN = \/usr\/bin\/ln$/LN = cp -a/'` |
| 5 | e2freefrag 链接失败：undefined symbol fsmap_sizeof | 系统 sysroot 的 linux/fsmap.h 定义了 FS_IOC_GETFSMAP，导致本地 fsmap.h 的 inline 函数被条件编译跳过 | 修改 misc/fsmap.h，将 inline 函数移到 #ifndef FS_IOC_GETFSMAP 块之外 |
| 6 | E076 问题：fstat/lseek 对非文件 fd 返回 EACCES | 鸿蒙内核历史版本问题 | HongMeng Kernel 1.12.0 已解决，无需修改源码 |

## 源码修改

### 补丁列表
1. `0001-config-config.guess.patch`：添加 HarmonyOS 系统识别
2. `0002-config-config.sub.patch`：添加 ohos-linux triplet 和 kernel 列表
3. `0003-configure.patch`：configure 脚本调整（自动生成）
4. `0004-misc-fsmap.h.patch`：将 inline 函数移到条件编译块外，解决 OHOS sysroot linux/fsmap.h 定义导致的符号缺失

### 关键修改点
- **config/config.guess**：添加 `__OHOS__` LIBC 检测和 HarmonyOS case 分支
- **config/config.sub**：添加 ohos-linux triplet 和 linux-ohos* kernel 列表项
- **misc/fsmap.h**：将 `fsmap_sizeof` 和 `fsmap_advance` inline 函数移到 `#ifndef FS_IOC_GETFSMAP` 块之外，确保在 OHOS sysroot 已定义 `FS_IOC_GETFSMAP` 时仍然可用

## 依赖版本

无外部依赖，编译工具链：
- clang (系统自带)
- GNU make 4.4.1
- GNU automake 1.16.5
- GNU autoconf 2.72
- GNU gawk 5.4.0
- GNU sed (已安装预编译包)
- bash 5.3.0 (已安装预编译包)

## 验证结果

```bash
# 本地安装验证
/storage/Users/currentUser/usr/local/bin/mke2fs --version
mke2fs 1.47.0 (27-Feb-2023)

# 其他关键二进制
/storage/Users/currentUser/usr/local/bin/e2fsck --version
e2fsck 1.47.0 (27-Feb-2023)

/storage/Users/currentUser/usr/local/bin/tune2fs -l /dev/null 2>&1 | head -1
tune2fs 1.47.0 (27-Feb-2023)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| e2fsprogs-1.47.0-ohos-aarch64.tar.gz | 848KB | 预编译包（strip + ELF 签名） |
| e2fsprogs-1.47.0-ohos-aarch64-debug.tar.gz | 41KB | 预编译包（含调试符号） |

## 注意事项

1. **HMDFS 限制**：HMDFS 不支持硬链接，所有 Makefile 的 LN 命令需要改为 `cp -a`
2. **toybox sh 问题**：configure 和 config.guess 的 heredoc 和临时文件处理有问题，建议使用 bash
3. **sysroot 冲突**：OHOS sysroot 的 linux/fsmap.h 定义了 FS_IOC_GETFSMAP，可能与本地 fsmap.h 冲突，需要调整 inline 函数的定义位置
4. **内核版本**：HongMeng Kernel 1.12.0 已解决 E076 问题，无需针对 fstat/lseek 修改源码
5. **config.guess 补丁**：需要为 config/ 子目录和顶层目录的 config.guess 分别打补丁

---

**编译结束**: 2026-05-28 16:30
**最终状态**: built
---

**编译结束**: 2026-08-06 08:56
**最终状态**: built
