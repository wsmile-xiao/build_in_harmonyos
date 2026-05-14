# chicken 5.4.0 — OpenHarmony 编译记录

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | chicken (Scheme-to-C compiler) |
| 版本 | 5.4.0 |
| 构建系统 | autotools (自定义 Makefile) |
| 目标平台 | ohos-aarch64 |
| 编译状态 | partial |
| 发布日期 | 2026-04-29 |

## 编译指导

### 编译命令

```bash
# Step 1: 初始化
python3 $SKILL_ROOT/scripts/ohc-run.py init-build chicken 5.4.0 \
  --url=https://code.call-cc.org/releases/5.4.0/chicken-5.4.0.tar.gz

# Step 2: 编译
cd ~/builds/chicken-5.4.0.work
make PLATFORM=linux PREFIX=$DEFAULT_PREFIX

# Step 3: 安装 (DESTDIR 模式)
make install DESTDIR=$TEST_PREFIX PLATFORM=linux PREFIX=$DEFAULT_PREFIX

# Step 4: 测试
make PLATFORM=linux PREFIX=$DEFAULT_PREFIX check

# Step 5: 打包
python3 $SKILL_ROOT/scripts/ohc-run.py package chicken 5.4.0

# Step 6: 收尾
python3 $SKILL_ROOT/scripts/ohc-run.py finish chicken 5.4.0 partial
```

### 编译注意事项

1. **必须指定 PLATFORM=linux**
   - chicken 使用自定义 Makefile 系统
   - 通过 PLATFORM 变量选择平台配置文件 (Makefile.linux)
   - 不使用标准 configure 脚本

2. **不支持并行编译**
   - 不要使用 make -j 参数
   - 编译时间约 200 秒

3. **DESTDIR 模式正确应用**
   ```bash
   # PREFIX 是运行时路径（编译进二进制）
   make PLATFORM=linux PREFIX=$DEFAULT_PREFIX
   
   # DESTDIR 是 staging 目录（打包用）
   make install DESTDIR=$TEST_PREFIX PLATFORM=linux PREFIX=$DEFAULT_PREFIX
   ```

4. **编译选项**
   - 默认使用 -Os (优化大小)
   - -fomit-frame-pointer (省略帧指针)
   - -fno-strict-aliasing (禁用严格别名)
   - -fwrapv (有符号溢出定义行为)

## 补丁清单

**补丁数: 0**

chicken 5.4.0 源码无需修改即可在鸿蒙平台编译。源码已包含预生成的 C 文件。

patches/ 目录为空。

## 已知限制

### 1. posix file-permissions 测试失败

**现象**:
```
Error: (posix-tests.scm:116) assertion failed: 
(equal? (file-permissions "posix-tests.out") 438)
```

**原因**: 鸿蒙平台 SELinux 限制，chmod 操作不完全生效

**影响**:
- 文件权限控制功能受限
- 不影响 Scheme 编译器核心功能
- chicken/csi/csc 等工具正常使用

**状态**: 标记为平台限制，编译状态为 partial

**参考**: SKILL.md §7 Gotchas - E046

### 2. 编译时间较长

完整编译约需 200 秒。

### 3. 大量预生成 C 文件

源码包含预生成的 C 文件（由 Scheme 编译生成），编译时直接使用这些文件。

## 功能验证

### 版本验证

```bash
$ chicken --version
CHICKEN
(c) 2008-2022, The CHICKEN Team
(c) 2000-2007, Felix L. Winkelmann
Version 5.4.0 (rev 1a1d1495)
linux-unix-clang-arm64 [ 64bit dload ptables ]
```

### 编译器功能

```bash
# 编译 Scheme 文件
$ echo '(print "Hello")' > hello.scm
$ csc hello.scm -o hello
$ ./hello
Hello
```

### 解释器功能

```bash
$ csi
CHICKEN
Version 5.4.0 ...

#;1> (+ 1 2)
3
#;2> (exit)
```

### egg 管理功能

```bash
$ chicken-status
$ chicken-install <egg-name>
```

## 测试结果

| 测试类型 | 结果 | 详情 |
|---------|------|------|
| 编译测试 | ✅ PASS | 编译成功，产物完整 |
| 功能测试 | ✅ PASS | chicken/csi/csc 正常 |
| posix 测试 | ⚠️ PARTIAL | 1 个失败 |
| 质量门禁 | ✅ PASS | G1-G4 全通过 |

**posix 测试**: 6376+ 通过，1 失败 (file-permissions)

## 产物清单

### 二进制文件 (bin/)
- chicken (2.7 MB)
- csi (231 KB)
- csc (240 KB)
- chicken-install (772 KB)
- chicken-uninstall (96 KB)
- chicken-status (121 KB)
- chicken-profile (84 KB)
- chicken-do (23 KB)
- feathers (1.9 KB)

### 库文件 (lib/)
- libchicken.so.11 (4.0 MB) - 动态库
- libchicken.a (7.5 MB) - 静态库
- chicken/11/*.import.so (44 个模块库)
- chicken/11/types.db

### 预编译包
- chicken-5.4.0-ohos-aarch64.tar.gz (22 MB)
- chicken-5.4.0-ohos-aarch64-debug.tar.gz (2.6 MB)
- install-chicken-5.4.0.sh (1.4 KB)

## 知识沉淀

- 平台限制: chmod SELinux (E046)
- 构建系统: 自定义 Makefile + PLATFORM
- DESTDIR 模式正确应用
- 无源码修改

## 安装方式

```bash
# 直接解压
tar xzf chicken-5.4.0-ohos-aarch64.tar.gz -C ~/usr/local

# 或使用安装脚本
cd packaging && sh install-chicken-5.4.0.sh ~/usr/local
```

---
*编译时间: 2026-04-29*
*编译者: openharmony-compile-agent*