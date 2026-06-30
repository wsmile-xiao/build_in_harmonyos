# fastbuild 1.19 适配笔记

## 编译环境
- 构建系统: cmake（原项目使用 .bff 自定义构建系统，为 OpenHarmony 适配创建了 CMakeLists.txt）
- 编译日期: 2026-06-13
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: published

## 编译步骤

1. 下载源码: v1.19.tar.gz
2. 创建 CMakeLists.txt 替代原项目 .bff 构建系统
3. 创建 Makefile wrapper 委托到 CMake build 目录
4. 创建 configure wrapper 翻译 autotools 参数为 CMake 参数
5. CMake 配置: bash configure --prefix=$DEFAULT_PREFIX
6. 编译: make -j2
7. 安装 staging: make install DESTDIR=$TEST_PREFIX
8. 本地安装验证: make install（不带 DESTDIR）
9. 真实功能测试: fbuild 构建 C 代码目标 TestObj 成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原项目无标准构建系统 | fastbuild 使用自身 .bff 配置构建 | 创建 CMakeLists.txt 适配 ARM64/musl/OpenHarmony 平台 |
| 2 | CMakeLists.txt 需适配 ARM64 | 原 .bff 配置含 x86_64 特定参数(-m64) | 移除 -m64，保留 -fno-rtti、-fno-exceptions，定义 __LINUX__ |
| 3 | 内嵌第三方库 | LZ4、xxHash、Zstd 已内嵌在源码 | 在 CMakeLists.txt 中作为静态库编译 |
| 4 | configure shebang /bin/bash 不存在 | OpenHarmony 无 /bin/bash | 使用 bash configure 直接调用 |
| 5 | CPUInfo.cpp CPUId 类型在 ARM64 未定义 | CPUId 条件包含 __LINUX__ 不限定架构 | 修改条件为 `__x86_64__ || _M_X64`，新增 ARM64/OHOS hybrid core 回退 |
| 6 | Thread.cpp pthread_timedjoin_np 缺失 | musl libc 不提供此 API | 将 __OHOS__ 加入 __APPLE__ 条件回退分支 |
| 7 | SystemMutex 锁文件无法创建 | /tmp 只读(HMDFS)，open() 返回 -1 → TryLock() 返回 false | 优先使用 $TMPDIR，其次 $HOME/tmp，最后才 fallback 到 /tmp |
| 8 | FileIO 临时目录无法创建 | /tmp 只读(HMDFS)，无法创建 /tmp/_fbuild.tmp/ | 同上：优先使用 $TMPDIR，其次 $HOME/tmp |

## 源码修改（7 个补丁）

1. **0001-CMakeLists.txt.patch**: 新增 CMake 构建配置，适配 ARM64/musl/OpenHarmony
2. **0002-Makefile.patch**: Makefile wrapper，委托到 CMake build 目录
3. **0003-configure.patch**: configure wrapper，翻译 autotools 参数为 CMake 参数
4. **0004-CPUInfo.cpp.patch**: 限制 CPUId 使用条件为 x86_64，新增 ARM64/OHOS hybrid core 回退
5. **0005-FileIO.cpp.patch**: 临时目录路径优先使用 TMPDIR/HOME/tmp 替代只读 /tmp
6. **0006-SystemMutex.cpp.patch**: 锁文件路径优先使用 TMPDIR/HOME/tmp 替代只读 /tmp
7. **0007-Thread.cpp.patch**: 新增 __OHOS__ 到 pthread_timedjoin_np 回退分支

## 依赖版本

- 内嵌 LZ4 1.10.0
- 内嵌 xxHash 0.8.2
- 内嵌 Zstd 1.5.7
- 无外部依赖

## 真实功能验证结果

### fbuild -version
```
FASTBuild v1.19 - Copyright 2012-2026 Franta Fulin - https://www.fastbuild.org
```

### fbuild 实际构建目标（TestObj）
```
$ fbuild -config test.bff TestObj
FBuild: OK: TestObj
Time: 0.156s
```
构建产物: hello.o (ELF relocatable, 64-bit LSB arm64, 1224 bytes)

### fbuild -showtargets
```
FBuild: List of available targets
	TestObj
```

### fbuild -showdeps TestObj
```
FBuild: Dependency database
ObjectList TestObj
```

### 错误处理
- 不存在配置文件: 退出码 254 ✅
- 不存在目标: 退出码 255 ✅

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| fbuild | 6.9MB | 主可执行文件（ELF64 aarch64, 动态链接 libc++_shared.so + libc.so） |
| fastbuild-1.19-ohos-aarch64.tar.gz | 1557KB | 预编译包（stripped + ELF 签名） |
| fastbuild-1.19-ohos-aarch64-debug.tar.gz | 5754KB | 调试符号包 |

## 注意事项

- fastbuild 原项目使用 .bff 自定义构建系统，无 configure/CMakeLists.txt
- 编译选项从 Clang15.bff 配置适配而来（移除 -m64 x86_64 选项）
- 无 make check 测试套件，使用实际 bff 构建验证功能
- **关键**: fbuild 在 OpenHarmony 上需要 TMPDIR 环境变量指向可写目录
- fbuild bff 语法要求 Compiler() 使用 .Executable 属性，ObjectList() CompilerOptions 包含 %1/%2 占位符

---

**编译结束**: 2026-06-13 15:23
**最终状态**: published
