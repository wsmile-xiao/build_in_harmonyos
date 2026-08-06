# chicken — OpenHarmony aarch64 Conan 配方

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | chicken (Scheme-to-C compiler) |
| 描述 | Scheme 程序语言编译器和解释器 |
| 官网 | https://call-cc.org |
| 构建系统 | custom (Makefile.linux，无 configure 脚本) |
| 目标平台 | HarmonyOS aarch64 (os=OHOS, armv8) |
| Conan 引用 | `chicken/5.4.0` |

## 可用版本

| 版本 | 状态 | 补丁数 | 发布日期 |
|------|------|--------|----------|
| 5.4.0 | built | 0 | 2026-04-29（conan 配方固化 2026-08-03） |

## 编译指导（v3.0 Conan 体系）

### 编译命令

```bash
# Step 1: init-build（下载源码 + 骨架创建）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build chicken 5.4.0 \
  --url=https://code.call-cc.org/releases/5.4.0/chicken-5.4.0.tar.gz

# Step 2: 编译（源码目录，无 configure，直接 make）
cd $BUILD_SRC_DIR
make PLATFORM=linux PREFIX=$DEFAULT_PREFIX C_COMPILER=clang -j1

# Step 3: 安装（DESTDIR staging，需 install wrapper 解决 E098/E174）
make install DESTDIR=$TEST_PREFIX PLATFORM=linux PREFIX=$DEFAULT_PREFIX \
  INSTALL_PROGRAM=<install-wrapper> -j1

# Step 4: 测试
make PLATFORM=linux PREFIX=$DEFAULT_PREFIX check

# Step 5: Conan 配方固化 + 验证
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init chicken 5.4.0
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify chicken 5.4.0

# Step 6: finish
python3 $SKILL_ROOT/scripts/ohc-run.py finish chicken 5.4.0 built
```

### 关键参数

- **PLATFORM**: 必须指定为 `linux`（使用 Makefile.linux）
- **C_COMPILER**: 从 Conan conf (`tools.build:compiler_executables`) 获取（R33），不依赖 shell 环境变量
- **INSTALL_PROGRAM**: install wrapper（cp+chmod 模拟 `install`，因 HarmonyOS toybox 缺 install 命令，E098/E174）
- **PREFIX**: 运行时安装路径（编译进二进制）
- **不支持并行编译**: 必须 `-j1`

## 补丁清单

**当前版本 (5.4.0): 无补丁**

chicken 5.4.0 源码无需修改即可在鸿蒙平台编译。源码已包含预生成的 C 文件。

## 已知限制

### 1. posix file-permissions 测试失败 (E046)

**现象**: `(file-permissions "posix-tests.out")` 不返回期望值 438

**原因**: 鸿蒙平台 SELinux 限制，chmod 操作不完全生效

**影响**:
- 文件权限控制功能受限
- 不影响 Scheme 编译器核心功能
- chicken/csi/csc 等工具正常使用

**解决**: 记录为平台限制，不阻塞编译（make check 6377 通过 / 1 失败）

**参考**: SKILL.md §7 Gotchas - E046

### 2. 不支持并行编译

chicken 编译不支持 make -j，必须使用单线程编译（-j1）。

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

### 工具链验证（conan test_package，R34 实质调用）

```bash
csi -version                                  # 解释器运行
csc test_hello.scm -o test_hello              # 编译器驱动
./test_hello                                  # 编译产物运行并断言
# → Hello from CHICKEN 5.4.0 / fact(10) = 3628800
```

## 包内容

Conan 包 (`chicken/5.4.0`) 包含：

- `bin/`: 9 个可执行文件
  - chicken, csi, csc
  - chicken-install, chicken-uninstall, chicken-status
  - chicken-profile, chicken-do, feathers
- `lib/`: 库文件
  - libchicken.so.11 (动态库)
  - libchicken.a (静态库)
  - chicken/11/*.import.so (43 个模块库)
- `include/chicken/`: 头文件
  - chicken.h, chicken-config.h
- `share/chicken/`: 文档和配置
  - doc/, manual/, types.db

## 安装说明（Conan）

```bash
conan install --requires=chicken/5.4.0 -pr:h=ohos-aarch64
# 或作为依赖加入 conanfile.py:
#   self.requires("chicken/5.4.0")
```

## 相关链接

- 官网: https://call-cc.org
- 文档: https://wiki.call-cc.org
- Eggs 仓库: https://wiki.call-cc.org/eggs
- 源码: https://code.call-cc.org/releases/

---
*维护者: openharmony-compile-agent*
