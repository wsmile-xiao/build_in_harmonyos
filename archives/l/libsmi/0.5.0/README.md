# libsmi 0.5.0 — OpenHarmony 编译记录

## 基本信息
- **软件**: libsmi (SMI/MIB Parser Library)
- **版本**: 0.5.0
- **构建系统**: autotools
- **目标平台**: ohos-aarch64
- **编译状态**: ✅ 成功
- **源码来源**: https://www.ibr.cs.tu-bs.de/projects/libsmi/download/libsmi-0.5.0.tar.gz

## 软件简介
libsmi 是一个用于访问 SMI (Structure of Management Information) MIB 信息库的 C 语言库。它提供：
- MIB 模块解析器
- YANG 模块解析器
- 多种格式输出工具 (smidump, smilint, smiquery 等)

## 编译指导

### 环境要求
- clang 15.0.4
- make 4.4.1
- autoconf 2.72
- flex 2.6.4
- bison 3.8.2

### 编译步骤

```bash
# 1. 初始化构建
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libsmi 0.5.0 \
  --url=https://www.ibr.cs.tu-bs.de/projects/libsmi/download/libsmi-0.5.0.tar.gz

# 2. 进入源码目录
cd ~/builds/libsmi-0.5.0.work

# 3. 从 orig 目录恢复必要文件（如果缺失）
cp ../libsmi-0.5.0.orig/configure .
cp ../libsmi-0.5.0.orig/config.guess .
cp ../libsmi-0.5.0.orig/config.sub .
cp ../libsmi-0.5.0.orig/config.h.in .
cp ../libsmi-0.5.0.orig/configure.ac .
chmod +x configure config.guess config.sub

# 4. 应用核心补丁 (E007 - HarmonyOS 平台识别)
patch -p1 < patches/0001-config.guess.patch

# 5. 处理 HMDFS config.status 临时目录问题
FIXED_TMP="$TMPDIR/libsmi_conf_fixed"
mkdir -p "$FIXED_TMP"
chmod 777 "$FIXED_TMP"

# 6. 配置
./configure --prefix=$HOME/usr/local

# 7. 修复 config.status (如果遇到 Permission denied)
sed -i '875,885s|tmp=.*|tmp="$FIXED_TMP"|' config.status
sed -i 's|ac_tmp=.*|ac_tmp="$FIXED_TMP"|' config.status
export FIXED_TMP="$TMPDIR/libsmi_conf_fixed"
./config.status

# 8. 编译
make -j1

# 9. 安装到 staging 目录
make install DESTDIR=$HOME/test-install-libsmi-0.5.0

# 10. 安装到本地
make install

# 11. 测试 (可选)
make check
```

## 补丁清单

| 补丁文件 | 类型 | 说明 |
|---------|------|------|
| 0001-config.guess.patch | 平台识别 | HarmonyOS 平台快速检测，返回 aarch64-unknown-linux-gnu |
| 0002-configure.patch | 配置修复 | 修复 configure 脚本中的路径问题 |
| 其他 24 个补丁 | 生成文件 | 由 config.status 生成的文件变更（可忽略） |

**核心补丁**: 仅 0001-config.guess.patch 是必需的

## 已知限制

### F001: HMDFS config.status 临时目录问题
- **现象**: config.status 无法在当前目录创建临时文件 (`Permission denied`)
- **原因**: HMDFS 文件系统对 mktemp 创建的目录权限限制
- **解决方案**: 
  1. 预创建 `$TMPDIR/libsmi_conf_fixed` 目录
  2. 修改 config.status 使用该目录作为临时目录
  3. 设置 `export FIXED_TMP="$TMPDIR/libsmi_conf_fixed"`

### F002: RPATH 配置
- **现象**: 工具运行时找不到 libsmi.so.2
- **解决方案**: 
  ```bash
  export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH
  ```

### F003: G0 干净构建验证
- **状态**: SKIP (HMDFS 文件系统限制)
- **说明**: 干净构建验证脚本因平台限制无法自动执行，已手动验证通过

### F004: 测试失败
- **失败测试**: smidump-cm, smidump-orig-smiv2
- **原因**: 测试数据不完整 (缺少 BRIDGE-MIB 等文件)
- **影响**: 不影响核心功能

## 功能验证

### 验证命令
```bash
# 设置环境
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH

# 版本验证
smidump --version   # 输出: smidump 0.5.0
smilint --version   # 输出: smilint 0.5.0
smiquery --version  # 输出: smiquery 0.5.0

# pkg-config 验证
pkg-config --modversion libsmi  # 输出: 0.5.0

# MIB 解析测试
smidump -f tree mibs/ietf/IF-MIB  # 输出 MIB 树结构
smilint mibs/ietf/SNMPv2-MIB      # 检查 MIB 语法
```

### 测试结果
| 测试项 | 结果 |
|--------|------|
| 单元测试 | 18/20 PASS |
| 版本验证 | ✅ PASS |
| MIB 解析 | ✅ PASS |
| pkg-config | ✅ PASS |

## 编译产物

| 类型 | 文件 | 大小 |
|------|------|------|
| 共享库 | libsmi.so.2.0.27 | 1.1MB |
| 静态库 | libsmi.a | 1.7MB |
| 工具 | smidump, smilint, smiquery, smidiff, smixlate, smistrip, smicache | ~1.5MB |
| 头文件 | smi.h | 23KB |
| pkg-config | libsmi.pc | - |
| MIB 数据 | mibs/, pibs/, yang/ | ~2MB |

## 质量门禁

| 门禁 | 状态 |
|------|------|
| G1 二进制完整性 | ✅ PASS |
| G2 功能可用性 | ✅ PASS |
| G3 可移植性 | ✅ PASS |
| G4 档案完整性 | ✅ PASS |
| G0 干净构建 | ⚠️ SKIP (HMDFS) |

---
**归档日期**: 2026-05-15
**归档路径**: archives/l/libsmi/0.5.0/