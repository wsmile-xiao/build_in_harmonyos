# sedutil 1.20.0 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am，GitHub archive 不含 autoreconf 产物）
- 编译日期: 2026-09-29
- 编译器: clang 15.0.4 / clang++ (aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 1. 生成 configure（GitHub archive tarball 不含 autoreconf 产物）
autoreconf -i        # 本地探索阶段；配方内用 aclocal→autoconf→autoheader→automake 直跑链

# 2. configure（OHOS 需前置 SDK llvm/lib 到 LD_LIBRARY_PATH，解决 lld 加载 libxml2.so.16）
export LLVM_LIB=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib
export LD_LIBRARY_PATH=$LLVM_LIB:$LLVM_LIB/aarch64-linux-ohos:$LD_LIBRARY_PATH
./configure --prefix=$DEFAULT_PREFIX

# 3. 编译（HMDFS 不支持 mkfifo，禁 -j2 并行 jobserver）
make -j1

# 4. 安装验证
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lld 加载 libxml2.so.16 报 symbol not found | LD_LIBRARY_PATH 中 usr/local/lib 的 libxml2 抢占 | LD_LIBRARY_PATH 前置 SDK llvm/lib |
| 2 | conftest 运行失败缺 libc++_shared.so | conan/configure 测试程序需要 libc++ 运行库 | LD_LIBRARY_PATH 加 llvm/lib/aarch64-linux-ohos |
| 3 | config.status 临时目录 Permission denied | HMDFS 子目录继承父目录属主（非当前用户）+ umask 077 | 工作目录放 $HOME/tmp 直属（属主=当前用户）；配方内 umask 077→022 |
| 4 | make -j2 jobserver mkfifo 失败 | HMDFS 不支持 mkfifo | 用 make -j1 |
| 5 | GitVersion.sh bad interpreter /bin/bash | OHOS 无 /bin/bash | shebang 改 #!/bin/sh |
| 6 | DtaDevLinuxNvme.h 编译错误 | <linux/version.h> 与项目内生成的 linux/Version.h 大小写冲突；OHOS 无旧内核 linux/nvme.h | 直接 include <linux/nvme_ioctl.h>（内核>=4.4） |
| 7 | cf_sha1 未声明 | usr/local/include/sha1.h（OpenBSD 版）遮蔽 cifra 头 | include 用相对路径 "pbkdf2/sha1.h" |
| 8 | linuxpba 链接失败 rm Is a directory | HMDFS 大小写不敏感：可执行目标 linuxpba 与源码目录 LinuxPBA 同路径 | 产物改名 sedutil-pba |
| 9 | conan create configure 不存在 | GitHub archive 不含 autoreconf 产物 | 配方 build() 内 _run_autogen 直跑链生成 |
| 10 | conan perl 污染致 autoconf Cwd.pm 失败 | tool_requires autoconf 拉入 conan perl/5.42.2 污染系统 perl | 仅 tool_requires automake，autoconf 用系统 hnp/bin |
| 11 | conan out-of-source 构建失败 | Makefile.am 假定 in-source（相对路径） | layout() 设 folders.build="." |
| 12 | refresh-patch 误生成构建产物补丁 | .work 无编辑追踪器走 fallback 扫描 | 重建干净 .work + snapshot 基线 + track 修改文件，走精准模式 |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| 0001-Common-DtaHashPwd.cpp.patch | sha1.h → pbkdf2/sha1.h 相对路径 |
| 0002-Makefile.am.patch | linuxpba → sedutil-pba（HMDFS 大小写冲突） |
| 0003-linux-DtaDevLinuxNvme.h.patch | 直接 include nvme_ioctl.h |
| 0004-linux-GitVersion.sh.patch | shebang /bin/bash → /bin/sh |

## 依赖版本

- 无第三方库依赖（configure.ac 仅检查 POSIX 基础头）
- 构建依赖: automake/1.18（tool_requires，制品仓已发布）；autoconf 2.72（系统 hnp/bin）

## 验证结果

```bash
./sedutil-cli --scan                 # rc=0 正常扫描
./sedutil-cli --validatePBKDF2       # 4 个 PBKDF2 测试向量全部通过（suite passed）
conan-verify sedutil 1.20.0          # G0-G4 + L2/L4/L5 全部 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| sedutil-cli | 主命令行工具（sbin） |
| sedutil-pba | 预启动认证程序（原 linuxpba，改名规避 HMDFS 大小写冲突） |
| docs/sedutil-cli.8 | man page |

## 注意事项

- sedutil-cli --validatePBKDF2 退出码 134（=0x86 DTAERROR_INVALID_COMMAND）系上游 main 流程
  break 后落入末尾 return 的设计，测试内容本身全部通过（suite passed）
- TestSuite.sh 需真实 SED 磁盘 + root，破坏性测试，OHOS 平台不可运行

---

**编译结束**: 2026-09-29 03:30
**最终状态**: built
