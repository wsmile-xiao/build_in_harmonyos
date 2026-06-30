# 编译笔记 — espeak 1.48.04

## 编译概要
- **软件**: espeak (语音合成器)
- **版本**: 1.48.04 (内部版本号显示 1.48.03)
- **日期**: 2026-05-26
- **构建系统**: 自定义 Makefile（非标准 autotools）
- **编译器**: clang 15.0.4 / clang++

## 依赖处理
- **portaudio 19.7.0**: 从 cmd-pkgs 预编译包安装（R18: 预编译优先）
  - `curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- portaudio 19.7.0`
  - 安装位置: ~/usr/local (DEFAULT_PREFIX)
  - pkg-config: portaudio-2.0 版本 19

## 适配修改

### 1. 源码修改 (pthread_cancel, E051)
- **文件**: src/event.cpp, src/fifo.cpp
- **问题**: `pthread_cancel` 在 OpenHarmony/musl 不支持
- **修复**: 使用 `#ifdef __OHOS__` 守卫，替换为 `sem_post` + `pthread_join`
  ```cpp
  #ifdef __OHOS__
    sem_post(&my_sem_stop_is_required);  // 唤醒线程
    pthread_join(my_thread, NULL);       // 等待线程退出
  #else
    pthread_cancel(my_thread);
    pthread_join(my_thread, NULL);
  #endif
  ```

### 2. Makefile 修改 (R20 DESTDIR 模式)
- **PREFIX**: `/usr` → `~/usr/local` (DEFAULT_PREFIX)
- **DATADIR**: `/usr/share/espeak-data` → `$DEFAULT_PREFIX/share/espeak-data`
- **CXX**: 默认 → `clang++`
- **AR**: 默认 → `llvm-ar`
- **EXTRA_LIBS**: 空 → `-lm` (数学库)
- **LDFLAGS**: 空 → `-L$DEFAULT_PREFIX/lib`
- **CXXFLAGS**: `-O2` → `-O2 -fPIC`
- **install 目标**: `$(INSTALL) -m 755` → `$(INSTALL_CMD)` + `chmod 755` (无 install 命令)
- **ln -sf**: 保持 `$(LN_SF) = /bin/ln -sf`，在 install 目标中改为 `rm -f && ln -s` (R5 HMDFS)

### 3. portaudio API 适配
- **文件**: src/portaudio.h
- **操作**: 复制 portaudio19.h 到 portaudio.h (portaudio v19 API)
- **说明**: espeak 源码自带 portaudio18.h 和 portaudio19.h，需要根据安装的 portaudio 版本选择

### 4. 编译命令
```bash
cd $BUILD_SRC_DIR/src
make CXX=clang++ AR=llvm-ar CXXFLAGS="-O2 -fPIC" \
     LDFLAGS="-L/storage/Users/currentUser/usr/local/lib" \
     USE_AUDIO="-DUSE_PORTAUDIO -D__OHOS__" -j2
make DESTDIR=$TEST_PREFIX install (相同参数)
make install (不带 DESTDIR，安装到 DEFAULT_PREFIX)
```

## 验证结果
- `espeak --version` → "eSpeak text-to-speech: 1.48.03  04.Mar.14"
- `speak --version` → "speak text-to-speech: 1.48.03  04.Mar.14"
- `espeak -w test.wav "Hello world"` → 45KB WAV 文件生成成功
- 无安全弹窗 (HongMeng Kernel 1.12.0)

**编译结束**: 2026-05-26 15:24
**最终状态**: published
---

**编译结束**: 2026-05-26 15:34
**最终状态**: published
