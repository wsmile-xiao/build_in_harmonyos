# chicken 5.4.0 — OpenHarmony 编译记录

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | chicken (Scheme-to-C compiler) |
| 版本 | 5.4.0 |
| 构建系统 | autotools (自定义 Makefile，无 configure 脚本) |
| 目标平台 | ohos-aarch64 |
| 编译状态 | **built** |
| 首次编译 | 2026-04-29 (partial，探索性编译) |
| Conan 配方固化 | **2026-08-03** (conan-verify 8 道门禁通过) |
| Conan 引用 | `chicken/5.4.0` |
| 补丁数 | 0（源码零修改） |

## 编译指导（Conan 体系，v3.0）

### 配方文件
- `conanfile.py` — 自定义 Makefile 构建配方（`make PLATFORM=linux PREFIX=... C_COMPILER=clang`）
- `conandata.yml` — 官方源码 + SHA256 校验（R39）
- `test_package/` — 实质调用工具链的 L1 测试（R34）

### 验证命令

```bash
# 生成配方
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init chicken 5.4.0

# 验证配方（8 道门禁 G0-G4 + L2/L4/L5）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify chicken 5.4.0

# 收尾（W2 结构 + W3 本地编译验证，状态 built）
python3 $SKILL_ROOT/scripts/ohc-run.py finish chicken 5.4.0 built
```

### 探索阶段编译命令（历史参考）

```bash
# 编译（无 configure 脚本，直接 make；不支持 -j）
make PLATFORM=linux PREFIX=$DEFAULT_PREFIX C_COMPILER=clang -j1

# 安装（HarmonyOS toybox 缺 install 命令，需注入 wrapper，见已知限制 #2）
make install DESTDIR=$TEST_PREFIX PLATFORM=linux PREFIX=$DEFAULT_PREFIX \
  C_COMPILER=clang INSTALL_PROGRAM=<install-wrapper> -j1

# 测试
make PLATFORM=linux PREFIX=$DEFAULT_PREFIX C_COMPILER=clang check
```

### 编译注意事项

1. **必须指定 PLATFORM=linux**
   - chicken 使用自定义 Makefile 系统
   - 通过 PLATFORM 变量选择平台配置文件 (Makefile.linux)
   - 不使用标准 configure 脚本

2. **不支持并行编译**
   - 不要使用 make -j 参数（R9：-j1）
   - 编译时间约 170-200 秒

3. **编译器指定**
   - 本机无 gcc，必须指定 `C_COMPILER=clang`
   - conanfile.py 中从 Conan conf 获取编译器路径（R33）

4. **编译选项**
   - 默认使用 -Os (优化大小)
   - -fomit-frame-pointer (省略帧指针)
   - -fno-strict-aliasing (禁用严格别名)
   - -fwrapv (有符号溢出定义行为)

## 补丁清单

**补丁数: 0**

chicken 5.4.0 源码无需修改即可在鸿蒙平台编译。源码已包含预生成的 C 文件。

patches/ 目录为空（无补丁不创建）。

## 已知限制

### 1. posix file-permissions 测试失败（E046 平台限制）

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

**状态**: 标记为平台限制（E046），不阻塞编译，测试结果记录在 reports/test-report.md

### 2. HarmonyOS toybox 缺 install 命令（E098/E174）

- `make install` 直接调用 `install` 命令会失败（`install: inaccessible or not found`）
- 解决方案：编写 cp+chmod 语义的 install wrapper，通过 `INSTALL_PROGRAM=` 注入 make
- wrapper 逻辑已固化在 conanfile.py 的 `_write_install_wrapper()` 中

### 3. 编译时间较长

完整编译约需 170-200 秒。

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

### test_package 实质验证（R34）

```bash
$ csi -version          # 解释器
CHICKEN 5.4.0 (rev 1a1d1495) linux-unix-clang-arm64

$ csc -o test_hello test_hello.scm && ./test_hello   # 编译器 + 运行
Hello from CHICKEN 5.4.0
fact(10) = 3628800
conan test_package: chicken toolchain OK
```

## 测试结果

| 测试类型 | 结果 | 详情 |
|---------|------|------|
| make check | ✅ 6377 通过 / 1 失败 | 唯一失败 posix file-permissions（E046 平台限制） |
| conan create | ✅ PASS | 干净源码构建 + test_package 实质测试通过 |
| 质量门禁 G0-G4 | ✅ PASS | 8 道门禁全部通过 |

## 产物清单

### 二进制文件 (bin/) — 9 个
- chicken (2.7 MB) - Scheme-to-C 编译器
- csi (231 KB) - 交互式解释器
- csc (240 KB) - 编译器驱动
- chicken-install (772 KB) - egg 包管理器
- chicken-uninstall (96 KB) - egg 卸载工具
- chicken-status (121 KB) - egg 状态查询
- chicken-profile (84 KB) - 性能分析
- chicken-do (23 KB) - 构建辅助
- feathers (1.9 KB) - 调试器前端

### 库文件 (lib/)
- libchicken.so.11 (4.0 MB) - 动态库
- libchicken.a (7.5 MB) - 静态库
- chicken/11/*.import.so (43 个模块库)
- chicken/11/types.db

### 头文件 (include/chicken/)
- chicken.h
- chicken-config.h

## Conan 配方固化（2026-08-03）

- **conan-verify**: G0-G4 + L2/L4/L5 全部 PASS（8 道门禁）
- **commands.json**: `archives/c/chicken/commands.json`（R38，工具类型，声明 9 个命令行工具）
- **W3 本地 CI 模拟**: setup.sh + build_and_test.sh 通过（conan create 真实执行）
- **状态**: built（conan-verify 通过，未 upload）

## 知识沉淀

- 平台限制: chmod SELinux (E046)
- 构建系统: 自定义 Makefile + PLATFORM，无 configure
- 工具缺失: install 命令不存在于 OHOS toybox (E098/E174)，wrapper 注入 INSTALL_PROGRAM
- Conan 配方: 自定义 Makefile 用 `make PLATFORM=linux PREFIX=... C_COMPILER=<conf> INSTALL_PROGRAM=<wrapper> -j1`（R33）
- 无源码修改

## 安装方式（Conan 体系）

```bash
# Conan 安装（配方已固化，未 upload 前本地缓存使用）
conan install --requires=chicken/5.4.0 -pr:h=ci/conan/profiles/ohos-aarch64

# 历史 v2.0 预编译包（2026-04-29，探索阶段产物）
# tar xzf packaging/chicken-5.4.0-ohos-aarch64.tar.gz -C ~/usr/local
```

---
*首次编译: 2026-04-29 (partial) | Conan 配方固化: 2026-08-03 (built)*
*编译者: openharmony-compile-agent*
