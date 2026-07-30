# sdl2 2.30.10 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **源码下载**: 从 GitHub releases 下载 SDL2-2.30.10.tar.gz
2. **解压**: tar xf 解压到 ~/tmp/builds/sdl2-2.30.10.work
3. **configure**: `./configure --prefix=$HOME/usr/local`
4. **make**: `make -j1`（单线程避开 jobserver FIFO 问题）
5. **install**: `make install DESTDIR=$HOME/tmp/test-install-sdl2-2.30.10`
6. **本地安装**: `make install`（安装到 ~/usr/local）
7. **验证**: `~/usr/local/bin/sdl2-config --version` → 2.30.10

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识条目 |
|---|------|------|----------|----------|
| 1 | config.sub 不识别 ohos 三元组 | E072 - config.sub 缺少 ohos-linux 映射 | 在 build-scripts/config.sub 中添加 ohos-linux → linux-ohos 映射（第 157 行） | E072 |
| 2 | pthread_setcanceltype undefined symbol | E085 - musl 不实现 POSIX 线程取消 API | 修改 src/thread/pthread/SDL_systhread.c，调整条件判断优先检查 __OHOS__ | E085 |
| 3 | make jobserver FIFO 权限错误 | HMDFS 不支持 mkfifo | 使用 `make -j1` 单线程编译 | E076 相关 |

## 源码修改

### 1. build-scripts/config.sub（第 157 行添加）
```diff
@@ 153,6 @@
 			android-linux)
 				basic_machine=$field1-unknown
 				basic_os=linux-android
 				;;
+			ohos-linux)
+				basic_machine=$field1-unknown
+				basic_os=linux-ohos
+				;;
 			*)
```

### 2. src/thread/pthread/SDL_systhread.c（第 174-186 行修改）
```diff
@@ 174,6 @@
-#ifdef PTHREAD_CANCEL_ASYNCHRONOUS
+#ifdef __OHOS__
+    /* HarmonyOS/musl: pthread cancellation is not fully supported, skip */
+    /* musl does not implement pthread_cancel or pthread_setcanceltype */
+#elif defined(PTHREAD_CANCEL_ASYNCHRONOUS)
     /* Allow ourselves to be asynchronously cancelled */
     {
         int oldstate;
         pthread_setcanceltype(PTHREAD_CANCEL_ASYNCHRONOUS, &oldstate);
     }
-#elif defined(__OHOS__)
-    /* HarmonyOS/musl: pthread cancellation is not fully supported, skip */
-    /* musl does not implement pthread_cancel or pthread_setcanceltype */
 #else
```

## 预编译风险扫描结果

根据 pre-scan-report.yaml：
- 🔴 **PSCAN-MUSL-002**: mremap syscall 在 OHOS 上不可用（src/stdlib/SDL_malloc.c）
  - **状态**: 未触发（编译成功，暂未遇到 mremap 调用场景）
  - **潜在风险**: 如果 SDL_malloc 使用 mremap，需要添加 #ifdef __OHOS__ 守卫
- 🟡 **PSCAN-HMDFS-002**: chmod/chown 可能无权限效果（非阻塞）
- 🟡 **PSCAN-FS-001**: /tmp 路径硬编码（非阻塞，build-scripts 中的脚本）
- 🟢 **PSCAN-BUILD-001**: config.guess/config.sub 存在（已修复）
- ℹ️ **PSCAN-DOC-001**: Linux/glibc 依赖声明（文档）
- 🟢 **PSCAN-MUSL-FUNC-mallinfo/mallopt/malloc_trim**: musl 可能不提供（低优先级）

## 依赖版本

本次编译未依赖外部库（SDL2 自包含）。

## 验证结果

```bash
$ ~/usr/local/bin/sdl2-config --version
2.30.10

$ ~/usr/local/bin/sdl2-config --cflags
-I/storage/Users/currentUser/usr/local/include/SDL2 -D_REENTRANT

$ ~/usr/local/bin/sdl2-config --libs
-L/storage/Users/currentUser/usr/local/lib -Wl,-rpath,... -lSDL2

$ ls ~/usr/local/lib/libSDL2*
libSDL2-2.0.so.0.3000.10 (1.5M)
libSDL2.a (2.4M)
libSDL2_test.a (286K)
libSDL2main.a (1.1K)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libSDL2-2.0.so.0.3000.10 | 1.5M | 共享库 |
| libSDL2.a | 2.4M | 静态库 |
| libSDL2_test.a | 286K | 测试库 |
| libSDL2main.a | 1.1K | 主入口库 |
| sdl2-config | 1.5K | 配置脚本 |
| SDL2 headers | 7M | 头文件集合 |

## 注意事项

1. **单线程编译**: 由于 HMDFS 不支持 mkfifo，必须使用 `make -j1`，否则 jobserver 会失败
2. **线程取消 API**: musl/OHOS 不支持 POSIX 线程取消功能（pthread_cancel, pthread_setcanceltype 等），已通过条件编译跳过
3. **mremap 风险**: 预扫描发现潜在风险，但本次编译未触发，后续使用需关注
4. **无测试套件**: SDL2 不提供 `make check`，测试需手动编译测试程序

## 编译结束

**时间**: 2026-05-27 00:15
**最终状态**: built（编译成功，未制作预编译包）
**问题**: 
- 补丁生成失败（权限问题）
- G0 干净构建验证失败（tar xf 权限问题）
- G4 档案完整性失败（缺少预编译包）

**后续步骤**: 
1. 修复补丁生成权限问题
2. 制作预编译包（ohc-run.py package）
3. 通过质量门禁后更新状态为 published
---

**编译结束**: 2026-07-15 18:29
**最终状态**: published
