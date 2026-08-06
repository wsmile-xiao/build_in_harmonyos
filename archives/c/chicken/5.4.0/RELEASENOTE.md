# chicken 5.4.0 — 版本发布说明

## 基本信息

| 项目 | 值 |
|------|-----|
| 版本 | 5.4.0 |
| 首次发布 | 2026-04-29 (探索性，partial) |
| Conan 配方固化 | **2026-08-03 (built)** |
| 构建系统 | autotools (自定义 Makefile，无 configure) |
| 目标平台 | HarmonyOS aarch64 |
| 编译状态 | **built** |
| Conan 引用 | `chicken/5.4.0` |
| 质量门禁 | **PASS（conan-verify 8 道 G0-G4 + L2/L4/L5）** |
| 补丁数 | 0 |

## 交付物（Conan 体系，v3.0）

| 文件 | 路径 | 说明 |
|------|------|------|
| conanfile.py | `archives/c/chicken/5.4.0/conanfile.py` | 自定义 Makefile 构建配方（CI 唯一输入） |
| conandata.yml | `archives/c/chicken/5.4.0/conandata.yml` | 官方源码 + SHA256（R39） |
| test_package/ | `archives/c/chicken/5.4.0/test_package/` | L1 实质测试（R34） |
| commands.json | `archives/c/chicken/commands.json` | 命令行工具声明（R38） |
| manifest.yaml | `archives/c/chicken/5.4.0/manifest.yaml` | 编译元数据（status=built） |
| notes.md | `archives/c/chicken/5.4.0/notes.md` | 适配笔记 |
| reports/ | `archives/c/chicken/5.4.0/reports/` | test-report / conan-verify-report / conan-create.log |

> 历史 v2.0 预编译包（2026-04-29 探索阶段产物 tar.gz/install.sh）已被 Conan 体系替代（R19），仅作历史参考保留。

## 包内容

### 二进制文件 (bin/) — 9 个
- `chicken` - Scheme-to-C 编译器 (2.7 MB)
- `csi` - Scheme 交互式解释器 (231 KB)
- `csc` - Scheme 编译器驱动 (240 KB)
- `chicken-install` - egg 包管理器 (772 KB)
- `chicken-uninstall` - egg 卸载工具 (96 KB)
- `chicken-status` - egg 状态查询 (121 KB)
- `chicken-profile` - 性能分析工具 (84 KB)
- `chicken-do` - 构建辅助工具 (23 KB)
- `feathers` - 调试器前端脚本 (1.9 KB)

### 库文件 (lib/)
- `libchicken.so.11` - 动态库 (4.0 MB)
- `libchicken.a` - 静态库 (7.5 MB)
- `chicken/11/*.import.so` - 43 个模块导入库
- `chicken/11/types.db` - 类型数据库

### 头文件 (include/chicken/)
- `chicken.h` - 主头文件
- `chicken-config.h` - 配置头文件

### 文档 (share/chicken/)
- `doc/README` - 软件说明
- `doc/LICENSE` - BSD 许可证
- `doc/manual/*.html` - HTML 手册
- `man/man1/*.1` - 手册页

## 编译参数（Conan 配方固化）

```bash
# conanfile.py build()
make PLATFORM=linux PREFIX=$package_folder C_COMPILER=<conan conf> \
  INSTALL_PROGRAM=<install-wrapper> -j1

# conanfile.py package()
make install PLATFORM=linux PREFIX=$package_folder INSTALL_PROGRAM=<install-wrapper> -j1
```

**关键变量**:
- PLATFORM=linux (使用 Makefile.linux，无 configure 脚本)
- C_COMPILER=clang（本机无 gcc，从 Conan conf 获取，R33）
- INSTALL_PROGRAM=install wrapper（E098/E174：HarmonyOS toybox 缺 install 命令）
- -j1（chicken 不支持并行编译，R9）

## 质量门禁（conan-verify 8 道）

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 预构建风险 | ✅ PASS | 无已知风险 |
| G1 配方完整性 | ✅ PASS | 字段/方法/test_package 齐全 |
| G2 conan create | ✅ PASS | 干净源码真实构建 + test_package 实质测试 |
| G3 系统同名库隔离 | ✅ PASS | 非系统同名库（R26 不适用） |
| G4 产物完整性 | ✅ PASS | 9 bin + 2 lib + 43 import + 2 header |
| L2 smoke test | ✅ PASS | csi/csc/chicken 版本验证 |
| L4 安全扫描 | ✅ PASS | NX + PIE + RELRO（readelf 实测） |
| L5 产物基线 | ✅ PASS | SHA256 基线记录 |

## 测试结果

| 测试类型 | 结果 | 说明 |
|---------|------|------|
| make check | ✅ 6377 通过 / 1 失败 | 唯一失败 posix file-permissions（E046 平台限制） |
| conan create + test_package | ✅ PASS | `Hello from CHICKEN 5.4.0 / fact(10)=3628800 / OK` |
| 质量门禁 G0-G4 + L2/L4/L5 | ✅ PASS | 8 道门禁全部通过 |

**posix 测试失败说明**:
- 测试: `file-permissions` (期望权限 438)
- 原因: 鸿蒙平台 SELinux 限制（E046，chmod 不生效）
- 影响: 不影响核心编译功能
- 记录: reports/test-report.md

## 补丁

**补丁数**: 0

chicken 5.4.0 源码无需修改即可在鸿蒙平台编译。

## 知识沉淀

- 平台限制: chmod 不完全生效（SELinux, E046）
- 构建系统: 自定义 Makefile，需指定 PLATFORM=linux，无 configure
- 工具缺失: install 命令不存在（E098/E174），cp+chmod wrapper 注入 INSTALL_PROGRAM
- 编译选项: -fno-strict-aliasing -fwrapv -Os -fomit-frame-pointer
- Conan 配方: R33 conf dict 读取编译器；R34 test_package 实质调用

## 安装说明（Conan 体系）

```bash
# Conan 安装（配方固化，发布后使用）
conan install --requires=chicken/5.4.0 -pr:h=ci/conan/profiles/ohos-aarch64
```

### 历史 v2.0 安装（探索阶段，仅参考）
```bash
# tar xzf packaging/chicken-5.4.0-ohos-aarch64.tar.gz -C ~/usr/local
# sh /path/to/archives/c/chicken/install.sh 5.4.0
```

## 环境要求

- HarmonyOS/OpenHarmony aarch64
- Conan 2.29.1（OHOS 适配版）
- clang 15.0.4（OHOS SDK 26.0.0.18）

## 版本验证

```bash
$ chicken --version
CHICKEN
Version 5.4.0 (rev 1a1d1495)
linux-unix-clang-arm64 [ 64bit dload ptables ]

$ csi -version
CHICKEN 5.4.0 (rev 1a1d1495) linux-unix-clang-arm64
```

---
*首次编译: 2026-04-29 (partial) | Conan 配方固化: 2026-08-03 (built)*
*编译者: openharmony-compile-agent*
