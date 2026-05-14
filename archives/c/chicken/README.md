# chicken — OpenHarmony aarch64 预编译包

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | chicken (Scheme-to-C compiler) |
| 描述 | Scheme 程序语言编译器和解释器 |
| 官网 | https://call-cc.org |
| 构建系统 | autotools (自定义 Makefile) |
| 目标平台 | HarmonyOS aarch64 |

## 可用版本

| 版本 | 状态 | 补丁数 | 发布日期 |
|------|------|--------|----------|
| 5.4.0 | partial | 0 | 2026-04-29 |

## 编译指导

### 编译命令

```bash
# Step 1: init-build
python3 $SKILL_ROOT/scripts/ohc-run.py init-build chicken 5.4.0 \
  --url=https://code.call-cc.org/releases/5.4.0/chicken-5.4.0.tar.gz

# Step 2: 编译 (源码目录)
cd ~/builds/chicken-5.4.0.work
make PLATFORM=linux PREFIX=$DEFAULT_PREFIX

# Step 3: 安装 (DESTDIR 模式)
make install DESTDIR=$TEST_PREFIX PLATFORM=linux PREFIX=$DEFAULT_PREFIX

# Step 4: 测试
make PLATFORM=linux PREFIX=$DEFAULT_PREFIX check

# Step 5: 打包
python3 $SKILL_ROOT/scripts/ohc-run.py package chicken 5.4.0

# Step 6: finish
python3 $SKILL_ROOT/scripts/ohc-run.py finish chicken 5.4.0 partial
```

### 关键参数

- **PLATFORM**: 必须指定为 `linux`（使用 Makefile.linux）
- **PREFIX**: 运行时安装路径（编译进二进制）
- **DESTDIR**: staging 目录（打包用）
- **不支持并行编译**: 不要使用 -j 参数

### 编译选项

```bash
C_COMPILER_OPTIONS = -fno-strict-aliasing -fwrapv -DHAVE_CHICKEN_CONFIG_H
C_COMPILER_OPTIMIZATION_OPTIONS = -Os -fomit-frame-pointer
```

## 补丁清单

**当前版本 (5.4.0): 无补丁**

chicken 5.4.0 源码无需修改即可在鸿蒙平台编译。源码已包含预生成的 C 文件。

## 已知限制

### 1. posix file-permissions 测试失败

**现象**: `(file-permissions "posix-tests.out")` 不返回期望值 438

**原因**: 鸿蒙平台 SELinux 限制，chmod 操作不完全生效

**影响**: 
- 文件权限控制功能受限
- 不影响 Scheme 编译器核心功能
- chicken/csi/csc 等工具正常使用

**解决**: 标记为平台限制，状态为 partial

**参考**: SKILL.md §7 Gotchas - E046

### 2. 不支持并行编译

chicken 编译不支持 make -j，必须使用单线程编译。

### 3. 编译时间较长

完整编译约需 200 秒（取决于机器性能）。

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

### 编译器验证

```bash
# 编译 Scheme 文件为 C
$ chicken hello.scm -output-file hello.c

# 使用 csc 编译为可执行文件
$ csc hello.scm -o hello
$ ./hello
```

### 解释器验证

```bash
$ csi
CHICKEN
(c) 2008-2022, The CHICKEN Team
(c) 2000-2007, Felix L. Winkelmann
Version 5.4.0 ...

#;1> (print "Hello, Scheme!")
Hello, Scheme!
#;2> (exit)
```

### egg 管理验证

```bash
$ chicken-status
$ chicken-install <egg-name>
```

## 包内容

每个版本的预编译包包含：

- `bin/`: 9 个可执行文件
  - chicken, csi, csc
  - chicken-install, chicken-uninstall, chicken-status
  - chicken-profile, chicken-do, feathers
- `lib/`: 库文件
  - libchicken.so.11 (动态库)
  - libchicken.a (静态库)
  - chicken/11/*.import.so (44 个模块库)
- `include/chicken/`: 头文件
  - chicken.h, chicken-config.h
- `share/chicken/`: 文档和配置
  - doc/, manual/, types.db

## 安装说明

### 方式 1: 直接解压

```bash
tar xzf chicken-5.4.0-ohos-aarch64.tar.gz -C ~/usr/local
```

### 方式 2: 使用安装脚本

```bash
cd archives/c/chicken/5.4.0/packaging
sh install-chicken-5.4.0.sh ~/usr/local
```

### 方式 3: 软件级安装脚本

```bash
sh archives/c/chicken/install.sh 5.4.0
```

## 环境要求

- HarmonyOS/OpenHarmony aarch64
- `~/usr/local/bin` 在 PATH 中
- `~/usr/local/lib` 为库搜索路径

## 相关链接

- 官网: https://call-cc.org
- 文档: https://wiki.call-cc.org
- Eggs 仓库: https://wiki.call-cc.org/eggs
- 源码: https://code.call-cc.org/releases/

---
*维护者: openharmony-compile-agent*