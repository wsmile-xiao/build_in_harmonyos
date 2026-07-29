# libfuse 3.18.2 适配笔记 (OHOS)

## 编译环境
- 构建系统: meson
- 编译日期: 2026-07-27
- 编译器: clang/clang++ (LLVM 15.0.4)
- 状态: built

## 编译步骤

```bash
# 1. 初始化
python3 scripts/ohc-run.py init-build libfuse 3.18.2 \
  --url=https://github.com/libfuse/libfuse/releases/download/fuse-3.18.2/fuse-3.18.2.tar.gz

# 2. 生成 Conan 配方
python3 scripts/ohc-run.py conan-init libfuse 3.18.2

# 3. 手动 Meson 编译测试
source .build-context-libfuse-3.18.2
cd $BUILD_SRC_DIR
CC=/data/service/hnp/bin/clang \
CXX=/data/service/hnp/bin/clang++ \
AR=/data/service/hnp/bin/llvm-ar \
RANLIB=/data/service/hnp/bin/llvm-ranlib \
meson setup builddir -Dutils=false -Dexamples=false -Dtests=false -Duseroot=false
ninja -C builddir
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conancenter 的 validate() 拒绝 OHOS | conanfile.py 只接受 Linux/FreeBSD | 添加 "OHOS" 到 validate 判断 |
| 2 | meson 找不到 ar 归档工具 | 子进程未继承 PATH | profile [buildenv] 中设置 PATH + AR |
| 3 | system_libs 中 dl/rt 链接 | OHOS libc 集成了 dl/rt | 对 OHOS 跳过 dl/rt 链接 |
| 4 | host_machine.system() 返回 'harmonyos' | 这是 OHOS 的规范行为 | meson.build 中不触发 any error 分支，但 mount.c 选择失败 |
| 5 | test_package CMake target libfuse::fuse3 找不到 | CMakeDeps 生成的目标名为 libfuse::libfuse | CMakeLists.txt 改为 libfuse::libfuse |
| 6 | test.c #ifdef 空壳测试 (R34 违规) | HAVE_STRUCT_FUSE_CMD_LINE_OPTS 无定义，测试永远走 #else | 移除条件编译，改为直接调用 fuse_opt_add_arg + fuse_version |
| 7 | conan create 链接 libfuse3.a 时报 pthread_cancel 未定义 | OHOS libc 无 pthread_cancel/pthread_setcancelstate | **待修复**: meson.build 增加 `cc.has_function('pthread_cancel')` 检测 → `HAVE_PTHREAD_CANCEL` config 宏，源码中用 `#if HAVE_PTHREAD_CANCEL` 守卫（meson define-to-0，非 #ifdef） |
| 8 | conan create 链接时报 unmount 未定义 | mount_bsd.c 使用 unmount()，OHOS 不支持 | **待修复**: 需 patch meson.build 让 harmonyos 走 mount.c 路径 |

## 已知的待办补丁

以下补丁需要开发者单独实现（当前 conan create 验证因链接问题 pending）：

1. **lib/meson.build**: 将 `host_machine.system().startswith('linux')` 改为 `in ['linux', 'harmonyos']`，使 OHOS 使用 mount.c 而非 mount_bsd.c
2. **lib/fuse_loop_mt.c**: `pthread_cancel`/`pthread_setcancelstate` 调用添加 `#if HAVE_PTHREAD_CANCEL` 守卫（POSIX 特性检测，非平台宏；meson define-to-0 须用 `#if` 而非 `#ifdef`）
3. **lib/fuse.c**: `pthread_cancel` 调用添加 `#if HAVE_PTHREAD_CANCEL` 守卫（POSIX 特性检测，非平台宏；meson define-to-0 须用 `#if` 而非 `#ifdef`）

> ⚠️ 禁止使用 `#ifdef __OHOS__`（R8）。必须通过 meson 的 `cc.has_function()` 做 POSIX 特性检测，将结果写入 `fuse_config.h`。libfuse 本身使用 `private_cfg.set('HAVE_XXX', ...)` 模式，应遵循此模式。

## 依赖版本

| 软件 | 版本 |
|------|------|
| meson | 1.11.1 |
| ninja | 1.13.1 |
| clang | 15.0.4 |
| CMake | 4.1.2 |

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (Meson-based, OHOS-ready) |
| conandata.yml | 上游源码 URL + SHA256 |
| test_package/ | 消费者验证测试 (调用 fuse_opt_add_arg + fuse_version) |
| manifest.yaml | 版本级元数据 |
| notes.md | 本适配笔记 |

## 注意事项

1. 当前配方为 Meson 构建系统，非 Autotools
2. OHOS 完整适配需要 3 个补丁 (见上)，当前 conan create 验证被链接问题阻塞
3. test_package 的 test.c 已调用 fuse_opt_add_arg() 和 fuse_version() 实质验证 API 可链接 (R34)
4. R32 规范: 所有 settings.os 判断使用 in ("Linux", "OHOS") 格式
5. 交叉编译时需设置 OHOS 工具链的 cross file 给 meson
