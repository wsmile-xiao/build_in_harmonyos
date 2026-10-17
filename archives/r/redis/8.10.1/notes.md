# redis 8.10.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 1. 下载源码并解压
wget -O redis-8.10.1.tar.gz "https://ghfast.top/https://github.com/redis/redis/archive/refs/tags/8.10.1.tar.gz"
tar xzf redis-8.10.1.tar.gz && cd redis-8.10.1

# 2. 应用补丁（musl 兼容性修复）
patch -p1 < patches/0001-threads_mngr-atomic-init.patch
patch -p1 < patches/0002-setproctitle-musl-compat.patch
patch -p1 < patches/0003-makefile-pthread-compat.patch
patch -p1 < patches/0004-pthread_compat-stub.patch

# 3. 编译（使用 MALLOC=libc 避免 jemalloc 在 musl 上的问题）
make CC=clang MALLOC=libc -j1

# 4. 安装到 staging 目录
make CC=clang MALLOC=libc install PREFIX=/path/to/staging
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C11 _Atomic 变量静态初始化为 NULL 失败 | C11 _Atomic 不能用非编译时常量初始化 | 0001补丁：改为动态初始化，在 ThreadsManager_init() 中设置 |
| 2 | program_invocation_name 未定义 | musl libc 不提供 GNU 扩展变量 | 0002补丁：用 `__GLIBC__` 宏守卫，musl 下跳过 |
| 3 | pthread_cancel/pthread_setcancelstate 链接失败 | musl libc 不实现 POSIX 线程取消 API (E085) | 0003+0004补丁：提供 stub 实现，加入 Makefile 编译目标 |
| 4 | 补丁 0003 在 8.10.1 上应用失败 | 8.10.1 的 REDIS_SERVER_OBJ 列表新增了 t_array.o sparsearray.o gcra.o vector.o fast_float_strtod.o client_comp.o | 重新生成 0003 补丁以匹配 8.10.1 的对象列表 |
| 5 | make install 触发重新编译并报 "cc: not found" | make install 也会调用默认 CC=cc，而 OHOS 上没有 cc | make install 时也传递 CC=clang MALLOC=libc |

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
Redis server v=8.10.1 sha=00000000:1 malloc=libc bits=64 build=b9e81e2df44c3f5c

$ redis-cli --version
redis-cli 8.10.1

$ redis-benchmark --version
redis-benchmark 8.10.1
```

## 与 8.6.0 的差异

- 补丁 0001、0002、0004 与 8.6.0 完全相同（相关源码未变化）
- 补丁 0003 需要重新生成，因为 8.10.1 新增了以下对象文件：
  - `t_array.o` — 数组数据类型
  - `sparsearray.o` — 稀疏数组
  - `gcra.o` — GCRA 限流算法
  - `vector.o` — 向量数据类型
  - `fast_float_strtod.o` — 快速浮点转换
  - `client_comp.o` — 客户端压缩
- conanfile.py 的 package() 方法中 make install 也需要传递 CC=clang

## 注意事项

- 必须使用 `MALLOC=libc` 参数，jemalloc 在 musl 上有问题
- conanfile.py 的 build() 和 package() 方法中 CC=clang 和 MALLOC=libc 是硬编码的
- ELF 签名是 HarmonyOS 上可执行的必要条件
- make install 也需要传递 CC=clang MALLOC=libc，否则会触发重新编译
---

**编译结束**: 2026-08-25 11:43
**最终状态**: built
