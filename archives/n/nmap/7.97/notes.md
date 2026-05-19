# nmap 7.97 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-18
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 1. 初始化
python3 ohc-run.py init-build nmap 7.97 --url=https://nmap.org/dist/nmap-7.97.tar.bz2

# 2. 配置（需要设置 TMPDIR）
export TMPDIR=~/.tmp
./configure --prefix=$HOME/usr/local

# 3. 编译（跳过 zenmap）
make nmap
make -C ncat
make -C nping

# 4. 安装
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识图谱 |
|---|------|------|----------|----------|
| 1 | configure: umask 077 创建临时目录权限拒绝 | E011: HMDFS 文件系统 UID 映射导致权限问题 | sed -i 's/umask 077/umask 022/g' configure | E011 |
| 2 | config.guess 无法识别 HarmonyOS | E007: GNU config.guess 不包含 HarmonyOS 检测 | 使用 patch-autotools-ohos.pl 打补丁 | E007 |
| 3 | config.status /tmp 只读 | E002: /tmp 文件系统只读 | sed -i 's|/tmp|"$TMPDIR"|g' config.status | E002 |
| 4 | sockaddr_storage 重定义 | E091: OHOS 内核头文件 linux/socket.h 与 musl sys/socket.h 冲突 | 在 #include <linux/if.h> 前添加 define-guard | E091 |

## 源码修改

### 0001-libpcap-sockaddr_storage-fix.patch
**文件**: libpcap/pcap-linux.c
**修改**: 在 `#include <linux/if.h>` 前添加 `#define sockaddr_storage __linux_sockaddr_storage` 守卫

### 0002-libdnet-tun-linux-sockaddr_storage-fix.patch
**文件**: libdnet-stripped/src/tun-linux.c
**修改**: 同上，添加 sockaddr_storage 重定义守卫

## 依赖版本

- pcre2: 系统自带
- zlib: 系统自带
- lua: 内嵌 liblua

## 验证结果

```bash
# nmap 二进制生成成功
ls -la nmap
# -rwxrwx--- 1 file_manager file_manager 3529216 May 18 16:06 nmap

# ncat 二进制生成成功
ls -la ncat/ncat
# -rwxrwx--- 1 file_manager file_manager 760320 May 18 16:06 ncat/ncat

# nping 二进制生成成功
ls -la nping/nping
# -rwxrwx--- 1 file_manager file_manager 842240 May 18 16:07 nping/nping
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| nmap | 3.5MB | 主扫描工具 |
| ncat | 760KB | netcat 替代工具 |
| nping | 842KB | ping 工具 |

## 注意事项

1. zenmap (Python GUI) 因缺少 Python build 模块未编译，可跳过
2. 所有 configure 脚本需要修复 umask 077 → umask 022
3. 所有 config.guess/config.sub 需要应用 HarmonyOS 补丁
4. 包含 linux/if.h 的源文件需要添加 sockaddr_storage 守卫
---

**编译结束**: 2026-05-18 16:18
**最终状态**: built
