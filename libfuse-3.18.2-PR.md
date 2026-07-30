## PR 信息
- **三方库名称**：libfuse (fuse3)
- **上游版本**：3.18.2
- **上游仓库地址**：https://github.com/libfuse/libfuse
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 10 | C 测试程序（test_syscalls.c, test_signals.c, test_abi.c, test_write_cache.c, test_setattr.c, test_want_conversion.c, release_unlink_race.c, readdir_inode.c, hello.c, stracedecode.c）|
| 集成测试 | 3 | Python pytest 脚本（test_examples.py, test_ctests.py, test_custom_io.py）通过 mount/umount 做端到端验证 |
| 其他测试 | 0 | — |
| **合计** | **13** | |

### 是否存在对上游测试用例的修改？
- [x] **否**，未修改上游任何测试用例

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1 | -9 | test_package 冒烟测试：调用 `fuse_opt_add_arg()` + `fuse_version()` 实质验证 API 可链接 (R34) |
| 集成测试 | 0 | -3 | pytest 集成测试均需挂载/卸载 FUSE 文件系统，OHOS 当前无 FUSE 内核模块 |
| 鸿蒙特有测试 | 0 | 新增 | 暂无 |
| **合计** | **1** | **-12** | |

---

## 上游测试用例修改说明
无。上游测试用例未做任何修改。

## 验证结果

### 编译验证
- 编译器: clang 15.0.4 (LLVM) + GNU ar 2.45
- 编译状态: ✅ 通过
- 构建系统: Meson 1.11.1 + Ninja 1.13.1
- 配置选项: `-Dexamples=false -Dutils=false -Dtests=false -Duseroot=false`

### 产物验证
| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | 17 个编译目标全部成功。1 warning（unused variable 'w' when HAVE_PTHREAD_CANCEL off，无害） |
| 产物存在性 | ✅ | 静态库 `lib/libfuse3.a`、7 个头文件（include/fuse3/）、pkg-config 文件（lib/pkgconfig/fuse3.pc） |
| ELF 格式 | ✅ | 静态库 .a 格式，无需 ELF 签名 |
| 运行测试 | ✅ | `test_package` 1/1 tests passed (100%) — `fuse_opt_add_arg()` API 链接验证 |
| 动态依赖 | 🔲 | 静态库无动态依赖。系统库依赖：pthread（已链接），dl/rt（OHOS 上已集成到 libc，跳过） |

### 补丁说明
共 4 个补丁，均使用 POSIX 特性检测（R8 合规，禁止 `#ifdef __OHOS__`）：

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| 0001 | `meson.build` | 添加 `cc.has_function('pthread_cancel')` → `HAVE_PTHREAD_CANCEL` |
| 0002 | `lib/meson.build` | 选择 mount.c（harmonyos 走 Linux 路径） |
| 0003 | `lib/fuse_loop_mt.c` | `pthread_cancel/setcancelstate` 加 `#if HAVE_PTHREAD_CANCEL` 守卫（meson define-to-0 须用 `#if` 非 `#ifdef`）；若未定义则关闭 se->fd 唤醒 worker 线程 |
| 0004 | `lib/fuse.c` | `pthread_cancel` 加 `#if HAVE_PTHREAD_CANCEL` 守卫（meson define-to-0 须用 `#if` 非 `#ifdef`） |

### 依赖
- 无外部 Conan 依赖（纯 C 库，仅需系统 pthread）

### 测试结论
- 总体评价: ✅ `conan create` 通过。静态库 libfuse3.a 编译成功，test_package 验证 API 可链接可调用（1/1 passed）
- 已知限制:
  1. OHOS 无 FUSE 内核模块（/dev/fuse），所有需挂载文件系统的上游测试无法运行
  2. `pthread_cancel`/`pthread_setcancelstate` 在 OHOS libc 缺失，通过 `HAVE_PTHREAD_CANCEL` POSIX 特性检测适配（R8 合规）
  3. R34 测试已修复：test.c 直接调用 `fuse_opt_add_arg()` + `fuse_version()`，移除原 #ifdef 空壳守卫

### 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conancenter 原配方 validate() 拒绝 os=OHOS | 只接受 Linux/FreeBSD | conanfile.py 添加 "OHOS"（R32） |
| 2 | Meson 找不到 ar 归档工具 | 子进程未继承 PATH | `AR` 环境变量通过 `Environment().define("AR", ...)` 设置 |
| 3 | CMake target `libfuse::fuse3` 不存在 | CMakeDeps 生成 `libfuse::libfuse` | CMakeLists.txt 改为 `libfuse::libfuse` |
| 4 | test.c #ifdef 空壳测试 (R34) | `HAVE_STRUCT_FUSE_CMD_LINE_OPTS` 无定义，永远走 #else | 移除条件编译，改调 `fuse_opt_add_arg` + `fuse_version` |
| 5 | 链接 libfuse3.a 时报 `pthread_cancel` 未定义 | OHOS libc 无此函数 | meson `cc.has_function()` 检测 → `#if HAVE_PTHREAD_CANCEL` 守卫（meson define-to-0，非 #ifdef） |
| 6 | 链接时报 `unmount` 未定义 | mount_bsd.c 调用 unmount() | patch meson.build 让 harmonyos 用 mount.c |
| 7 | 0003 patch for 循环体移位 (UB) | 无花括号 for 循环内 `#ifdef` 导致 `pthread_mutex_unlock` 被当循环体 | `#ifdef` 移到整个 for 循环外侧 |
| 8 | 0003 patch worker 线程死锁 | 无 pthread_cancel 时 worker 永不退出 | `#else` 关闭 se->fd 唤醒 worker 线程 |

### 验证命令
```bash
conan create archives/l/libfuse/3.18.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing

# 输出示例
# [17/17] Linking static target lib/libfuse3.a
# test_libfuse ..... Passed    0.07 sec
# 100% tests passed, 0 tests failed out of 1
```

## 补充说明
- 本 PR 为 libfuse 首次 OHOS 适配。由于 FUSE 是用户态文件系统框架的核心依赖库，需先合入本 PR 并发布到制品仓，下游依赖方（如 sshfs）才能完成完整适配。
- OHOS 上 FUSE 内核模块尚未就绪，当前交付的是静态库 + 头文件 + API 可用性验证。待内核模块就绪后可补充上游测试套件。
- 1 个编译 warning（`unused variable 'w'`，仅在 HAVE_PTHREAD_CANCEL 未定义时触发）无害。
