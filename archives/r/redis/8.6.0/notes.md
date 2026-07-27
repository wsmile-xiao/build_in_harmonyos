# redis 8.6.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 1. 下载源码并解压
wget https://github.com/redis/redis/archive/refs/tags/8.6.0.tar.gz
tar xzf 8.6.0.tar.gz && cd redis-8.6.0

# 2. 应用补丁（musl 兼容性修复）
patch -p1 < patches/0001-threads_mngr-atomic-init.patch
patch -p1 < patches/0002-setproctitle-musl-compat.patch
patch -p1 < patches/0003-makefile-pthread-compat.patch
patch -p1 < patches/0004-pthread_compat-stub.patch

# 3. 编译（使用 MALLOC=libc 避免 jemalloc 在 musl 上的问题）
make MALLOC=libc -j2

# 4. 安装到 staging 目录
make install PREFIX=/path/to/staging
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C11 _Atomic 变量静态初始化为 NULL 失败 | C11 _Atomic 不能用非编译时常量初始化 | 0001补丁：改为动态初始化，在 ThreadsManager_init() 中设置 |
| 2 | program_invocation_name 未定义 | musl libc 不提供 GNU 扩展变量 | 0002补丁：用 `__GLIBC__` 宏守卫，musl 下跳过 |
| 3 | pthread_cancel/pthread_setcancelstate 链接失败 | musl libc 不实现 POSIX 线程取消 API (E085) | 0003+0004补丁：提供 stub 实现，加入 Makefile 编译目标 |

## 源码修改

- `src/threads_mngr.c` — 原子变量改为动态初始化
- `src/setproctitle.c` — GNU 扩展变量守卫
- `src/Makefile` — 添加 pthread_compat.o 到编译目标
- `src/pthread_compat.c` — 新增文件，pthread_cancel 等 stub 实现

## 依赖版本

- 无外部依赖（redis 使用内置 deps/ 目录中的依赖）
- 系统库：musl libc, pthread

## 验证结果

```bash
$ redis-server --version
Redis server v=8.6.0 sha=00000000:1 malloc=libc bits=64 build=2d811264082f5e58
```

## 注意事项

- 必须使用 `MALLOC=libc` 参数，jemalloc 在 musl 上有问题
- conanfile.py 的 build() 方法中 MALLOC=libc 是硬编码的
- ELF 签名是 HarmonyOS 上可执行的必要条件
---

**编译结束**: 2026-07-15 18:52
**最终状态**: built
