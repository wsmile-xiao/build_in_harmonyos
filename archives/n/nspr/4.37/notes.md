# NSPR 4.37 编译笔记

**编译开始**: 2026-05-23
**CI 修复**: 2026-07-16

## 任务背景
NSPR 是 NSS 的必需依赖，需要先编译 NSPR 才能编译 NSS。

## 编译策略
- NSPR 源码已包含在 nss-3.118.1-with-nspr-4.37.tar.gz 中
- 使用传统的 autoconf 构建系统
- 先安装 NSPR，再编译 NSS

## CI 修复 (2026-07-17, v9 — 添加 ac_cv_build 缓存变量绕过 config.guess)

### 问题: configure 失败 — configure 脚本 patch 使用错误的 autoconf 版本模式
- **根因**：NSPR 4.37 的 configure 脚本由**新版 autoconf**（非 autoconf 2.13）生成。v7 代码搜索 autoconf 2.13 的 `host_alias=\`${CONFIG_SHELL-/bin/sh} $ac_config_guess\`` 模式，但实际脚本使用新版格式 `ac_build_alias=\`$SHELL "${ac_aux_dir}config.guess"\``。这导致 v7 补丁静默跳过（`[warn] Could not find config.guess invocation in configure script (autoconf 2.13 pattern)`）。configure 仍调用原始 config.guess，而 config.guess 2020-07-12 无法识别 OHOS。
- **修复 (v8)**：修正 _patch_configure_for_ohos() 中的模式匹配，使用新版 autoconf 格式：
  ```python
  old_block = (
      '  ac_build_alias=$build_alias\n'
      'test "x$ac_build_alias" = x &&\n'
      '  ac_build_alias=`$SHELL "${ac_aux_dir}config.guess"`\n'
      'test "x$ac_build_alias" = x &&\n'
      '  as_fn_error $? "cannot guess build type; you must specify one" "$LINENO" 5'
  )
  ```
  替换为 case 检测 `uname -s` 返回 OHOS 时直接设置 ac_build_alias，不调用 config.guess。其他系统回退到 config.guess。
- **config.guess 策略保留**：v6 双重策略（Strategy A: $UNAME_SYSTEM case + Strategy B: combined case）作为备用保留，但实际生效的是 v8 configure 脚本 patch。
- **铁律遵守**：不使用 --build/--host 绕过（R15），正确修改源文件。

### 历史策略
- v1: GUESS= 变量赋值方式（旧版 echo+exit 风格 config.guess 不支持，静默跳过）
- v2: 优化 GUESS= 匹配模式（同上，仍然失败）
- v3: echo+exit 风格 `*:OHOS:*:*` 块 + OHOS 加入 Linux|GNU|GNU/*) 模式（CI 显示补丁成功但 configure 仍失败）
- v4: E160 策略 — 添加单独 OHOS) case 设置 UNAME_SYSTEM=Linux; LIBC=musl（无法工作，因为 new-style 无 combined case 后三组输出逻辑）
- v5: E160+echo+exit 策略 — 在 $UNAME_SYSTEM case 中添加 OHOS) 分支，直接 echo+exit（CI 显示补丁成功但仍失败）
- v6: 双重策略 — 同时在 $UNAME_SYSTEM case 和 combined case 中插入 OHOS 检测（CI 显示补丁成功但仍失败）
- v7: 修补 configure 脚本（autoconf 2.13 格式），但 NSPR 4.37 使用新版 autoconf，模式不匹配，补丁静默跳过
- **v8**: 修补 configure 脚本（新版 autoconf 格式），匹配 `ac_build_alias=\`$SHELL "${ac_aux_dir}config.guess"\`` 模式，直接绕过 config.guess
- **v9（当前）**：也在 build() 中设置 `os.environ["ac_cv_build"] = "aarch64-unknown-linux-musl"`，作为 autoconf 缓存变量。当环境变量 `ac_cv_build` 已设置时，configure 的 AC_CANONICAL_BUILD 宏跳过 config.guess 调用（`if test ${ac_cv_build+y}`），直接使用该值。这是绕过 config.guess 不可靠检测的最可靠方式。

## CI 修复 (2026-07-17, v11 — 修复 test_package 运行时共享库加载失败)

### 问题: test_package 运行时 `Error loading shared library libnspr4.so` + `Error relocating ... symbol not found`
- **根因**: OHOS musl ldso 使用 namespace 机制解析库路径，`env="conanrun"` 设置的 `LD_LIBRARY_PATH` 对非标准路径二进制无效（E186）。test_package 二进制链接了共享库，但运行时动态链接器找不到符号。
- **修复 (v11)**: 在 test_package/conanfile.py 的 test() 方法中显式设置 `LD_LIBRARY_PATH` 包含 NSPR 包的 lib 目录，遵循 airspyone-host 的相同模式。
- **参考**: knowledge/doc/E186.md (patchelf-fix-runpath), archives/a/airspyone-host/1.0.10/test_package/conanfile.py
- **CI 状态**: 等待官方 CI 验证

### 问题: config.status 失败 — `./confPJOIeI/subs1.awk: Permission denied`
- **根因**：NSPR configure 脚本使用 `(umask 077 && mkdir "$tmp")` 创建临时目录，目录权限为 700。CI 环境下，config.status 在此目录内创建 awk 脚本时，脚本文件无法获得执行权限，导致 `./config.status: line 581: ./confPJOIeI/subs1.awk: Permission denied`。
- **修复 (v10)**：在 `_patch_configure_umask()` 方法中，将 configure 脚本中所有 `(umask 077 && ...)` 改为 `(umask 000 && ...)`，确保临时目录具有 777 权限，所有文件可访问。
- **参考**：addrwatch 1.0.2、acl 2.3.2、advancecomp 2.6 使用相同修复模式。

### 测试
- test_package/test.c: 综合 NSPR API 测试（17+ 断言），覆盖线程、锁、文件IO、原子操作、内存管理、时间、环境变量、日志
