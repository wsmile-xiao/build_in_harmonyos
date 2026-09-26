# hashrat 1.25 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，内嵌 libUseful-bundled 5.45）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4 (OHOS SDK)
- 状态: built（本地 W3 待 conan-verify/finish 后确认）

## 编译步骤

```bash
# 官方源码（tag v1.25，SHA-256 4414dcfb...）
# GitHub 主站超时，经 codeload 官方下载，两端 SHA-256 一致
./configure --prefix=$DEFAULT_PREFIX --enable-largefiles
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure config.status 失败：`can't create .../confmpdnof/subs1.awk: Permission denied` | HMDFS 账户共享将新建文件属主映射为 account uid（20001006），与本进程 uid（20020101）不一致；autoconf `(umask 077 && mktemp -d)` 生成的 0700 临时目录对本进程不可写 | build() 内联将 configure 的 `mktemp -d` 替换为 `mkdir` 回退（4ti2 同款修复，脚本级 OHOS 守卫） |
| 2 | Socket.c 编译失败：`redefinition of 'sockaddr_storage'`（linux/socket.h vs sys/socket.h） | OHOS sysroot 中 linux/netfilter_ipv4.h → linux/socket.h 与 musl sys/socket.h 重复定义 sockaddr_storage（E091/E119 模式） | 补丁：`#ifdef __OHOS__` define-guard 临时重命名 sockaddr_storage，include 后 #undef |
| 3 | Process.c 编译失败：`redefinition of 'prctl_mm_map'`（linux/prctl.h vs sys/prctl.h） | OHOS sysroot 中 linux/prctl.h 与 sys/prctl.h 重复定义 struct prctl_mm_map | 补丁：OHOS 下删除 linux/prctl.h 引入（sys/prctl.h 已含所需全部 PR_* 常量） |
| 4 | make check 超时（240s 在 Repeated Iterations 段） | whirlpool/jh384 1000 次迭代 CPU 密集 | 逐算法补跑：whirlpool 1000-iter PASS、jh384 1000-iter PASS，md5/sha1/sha256/sha384 在 240s 窗口内已 OKAY |
| 5 | check.sh 直接执行失败 `No such file or directory`（shebang /bin/bash） | OHOS 无 /bin/bash，bash 位于 /data/service/hnp/bin/bash | 显式 `/data/service/hnp/bin/bash ./check.sh` 执行（配方 test 与本地验证均用显式 bash） |
| 6 | 上游 "Checking files" 用例 FAIL（期望 sha256 d50f1b...，实测 8ff7d1...） | 用例对 `-c 2>&1 | hashrat -sha256` 的合并流做整流哈希；上游期望 stderr 先于 stdout 写入（对应字节序 `\nChecked 1 files. 0 Failures\ntests/quotes.txt: OKAY\n`），本机构建因 stdout 缓冲先落盘（main.c fflush 时机差异）导致字节序不同 | 功能正确：文件校验 OKAY、0 Failures，且 "CheckHash exit codes correct" 用例通过；如实记录为上游管道字节序断言差异，计入台账 48/49 |

## 源码修改

补丁 `patches/0001-hashrat-1.25-ohos-kernel-header-clash.patch`（仅 OHOS 平台宏守卫，其他平台行为不变）：
- libUseful-bundled/Socket.c: netfilter 头引入处 define-guard sockaddr_storage
- libUseful-bundled/Process.c: OHOS 下省略 linux/prctl.h

## 依赖版本

- openssl/3.5.6（制品仓已发布）
- zlib/1.3.1（制品仓已发布）

## 验证结果

```bash
# 上游测试（check.sh，49 断言组，实测 48/49 通过）
/data/service/hnp/bin/bash ./check.sh   # "Checking files" 为管道字节序差异（见 #6）
# CLI 冒烟
./hashrat -version                       # version: 1.25
echo -n '<向量>' | ./hashrat -sha256     # c7fadad016311a935a56dcdfb585cf5a4781073f7da13afa22177796e566434f
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/hashrat | CLI 可执行文件（arm64, 动态链接 musl） |
| share/man/man1/hashrat.1 | 手册页 |

## 注意事项

- hashrat 为 CLI 工具（非库），软件级 commands.json 已声明（R38）
- 消费者用例：test_package 直接执行 bin/hashrat 的 -version 与 sha256 已知向量断言
---

**编译结束**: 2026-09-24 21:31
**最终状态**: published
