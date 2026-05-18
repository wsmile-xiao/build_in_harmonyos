# E093: socat 在 HarmonyOS 上可直接编译，无需修改源码

**分类**: platform_success  
**严重级别**: info  
**软件**: socat 1.7.4.4  
**创建日期**: 2026-05-14  
**贡献者**: 4E02

---

## 问题现象

在 HarmonyOS (HongMeng Kernel 1.12.0, musl libc) 上编译 socat 时，预期需要修改源码以适配平台差异，但实际上 autotools 构建系统自动完成了所有适配工作。

## 根因分析

socat 使用 autotools 构建系统，其 configure 脚本经过精心设计，能够：

1. **自动检测平台特性**: 通过 config.guess/config.sub 正确识别 HarmonyOS 平台
2. **检测 musl libc 限制**: 自动检测 musl 缺失的函数（如 isastream）
3. **禁用不适用的功能**: 当 isastream 不可用时，自动禁用 WITH_ABSTRACT_UNIXSOCKET
4. **无需手动干预**: 整个编译过程无需修改任何源码文件

## 解决方案

直接使用标准编译流程：

```bash
# 1. Configure
cd ~/tmp/builds/socat-1.7.4.4.work
./configure --prefix=/storage/Users/currentUser/usr/local

# 2. Build
make -j2

# 3. Install to staging
make install DESTDIR=/storage/Users/currentUser/tmp/test-install-socat-1.7.4.4

# 4. Install to local (模拟用户部署)
make install

# 5. 验证
socat -V
```

## 编译产物

成功编译后生成的二进制文件：

- **socat** (302K): 主程序，支持 TCP/UDP/UNIX socket 等多种协议
- **procan** (70K): 进程分析工具
- **filan** (78K): 文件 descriptor 分析工具

所有二进制文件都已通过 ELF 签名，可直接在 HarmonyOS 上执行。

## 验证方法

```bash
# 检查版本信息
socat -V

# 应显示:
# socat version 1.7.4.4 on May 14 2026 16:08:01
# running on HarmonyOS version #1 SMP Mon Mar 23 01:51:20 UTC 2026
# release HongMeng Kernel 1.12.0, machine aarch64

# 检查支持的功能
socat -V | grep "#define WITH"
```

## 平台兼容性记录

### musl 兼容性

| 功能 | 状态 | 说明 |
|------|------|------|
| `_res` state | ⚠️ 保留 | 已废弃但仍保留结构体定义，configure 检测到但未阻塞 |
| `isastream()` | ❌ 不可用 | musl 不实现，configure 自动检测并禁用 WITH_ABSTRACT_UNIXSOCKET |

### HMDFS 限制

| 功能 | 影响 | 处理 |
|------|------|------|
| chmod/chown | ⚠️ 中等 | HMDFS 上可能无权限效果，记录为平台限制，非阻塞 |
| 符号链接测试 | ⚠️ 低 | test.sh 中使用符号链接，可能失败，需跳过相关测试 |

## 适用范围

本经验适用于：

- 使用 autotools 构建系统的网络工具（如 socat, netcat, wget, curl 等）
- 需要在 HarmonyOS/musl 环境下编译的 C/C++ 软件
- 依赖 POSIX socket API 的软件

## 关键要点

1. **autotools 的优势**: 自动检测平台特性，减少手动适配工作
2. **musl 兼容性**: 大部分 POSIX 功能可用，少数 Linux 特有函数缺失
3. **HMDFS 限制**: 某些 POSIX 操作（chmod/chown）可能无效，但通常非阻塞
4. **无源码修改**: 本案例中 `.edit-tracker.json` 显示 `"edited": []`，无任何源码修改

## 相关知识条目

- **E007**: config.guess 平台检测失败（手动修改 config.guess）
- **E051**: syscall 未实现（setreuid/chroot 等）
- **E046**: chmod 权限限制（SELinux/HMDFS）

## 参考资料

- socat 官网: http://www.dest-unreach.org/socat/
- 编译记录: `archives/s/socat/1.7.4.4/notes.md`
- 预扫描报告: `~/tmp/builds/socat-1.7.4.4.work/.pre-scan-report.yaml`

---

**状态**: ✅ 已验证  
**质量门禁**: G1-G4 通过 (G0 因 HMDFS 限制未通过，已提供替代验证方案)  
**预编译包**: socat-1.7.4.4-ohos-aarch64.tar.gz (626K)