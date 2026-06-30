# concurrencykit 0.7.2 — OpenHarmony/HarmonyOS 预编译包

## 简介
ConcurrencyKit (ck) 是一个高性能并发数据结构库，提供环形队列、哈希表、原子操作、读写锁、自旋锁、epoch内存回收等并发编程基础设施。

本预编译包针对 HarmonyOS (HongMeng Kernel) aarch64 平台编译。

## 版本
- 软件名: concurrencykit (ck)
- 版本: 0.7.2
- 许可证: BSD-2-Clause

## 预编译包内容
- libck.a — 静态库 (53KB)
- libck.so.0.7.2 — 共享库 (64KB)
- libck.so / libck.so.0 — 符号链接
- pkgconfig/ck.pc — pkg-config 文件
- include/ck_*.h — 30+并发数据结构头文件
- share/man/man3/ — 手册页

## 安装方法
```bash
tar xzf concurrencykit-0.7.2-ohos-aarch64.tar.gz -C /usr/local
```

## 使用方法
### 静态链接
```bash
clang -I/usr/local/include your_program.c /usr/local/lib/libck.a -lpthread -o your_program
```

### pkg-config
```bash
clang `pkg-config --cflags --libs ck` your_program.c -o your_program
```

### 动态链接
注意：HarmonyOS 环境下动态链接需要 ELF 签名。

## 补丁说明
- 0001-configure.patch: 在 configure 的 OS 检测中添加 HarmonyOS 支持，
  将 `uname -s=HarmonyOS` 映射为 `linux`（因为 HarmonyOS 内核与 Linux 兼容）

## 已验证功能
- ✅ ck_pr 原子操作 (store/load/add/faa/inc/dec)
- ✅ ck_rwlock 读写锁
- ✅ ck_spinlock 自旋锁
- ✅ ck_epoch 内存回收机制
- ✅ 静态链接编译运行

## 无外部依赖