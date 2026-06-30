# libnghttp2 1.69.0 编译笔记

## 编译状态

**最终状态**: built
**构建系统**: CMake（Autotools 失败后改用）

## 问题与解决方案

### 问题 1: Autotools configure 在 HMDFS 上失败

**现象**:
```
./config.status[1154]: can't create /storage/Users/currentUser/tmp/confVskLaa/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**根因**: HMDFS 文件系统对临时文件创建有严格限制，Autotools 的 config.status 尝试在当前目录创建临时文件失败。

**解决方案**: 改用 CMake 构建，CMake 对 HMDFS 兼容性更好。

### 问题 2: config.guess 无法识别 HarmonyOS

**现象**: `config.guess` 返回 `aarch64-unknown-linux-ohos`，但 Autotools 不识别此三元组。

**解决方案**: 替换 config.guess/config.sub 为支持 linux-ohos 的版本。

## 编译步骤（CMake）

```bash
# 清理 Autotools 产物
cd ~/tmp/builds/libnghttp2-1.69.0.work
rm -rf configure config.status Makefile

# CMake 构建
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=ON ..
make -j2
make install DESTDIR=$TEST_PREFIX

# 打包
python3 $SKILL_ROOT/scripts/ohc-run.py package libnghttp2 1.69.0

# 验证
make install  # 安装到本地
```

## 质量门禁

| 门禁 | 结果 |
|------|------|
| G0 干净构建 | N/A（CMake 构建未验证）|
| G1 二进制完整性 | PASS |
| G2 功能可用性 | PASS |
| G3 可移植性 | PASS |
| G4 档案完整性 | PASS |

## 产物

- **核心库**: lib/libnghttp2.so
- **头文件**: include/nghttp2/nghttp2.h, nghttp2ver.h
- **CMake 配置**: lib/cmake/nghttp2/*.cmake
- **pkg-config**: lib/pkgconfig/libnghttp2.pc

## 建议

1. 后续版本优先使用 CMake 构建
2. Autotools 在 HMDFS 上有通用问题，可考虑平台级修复
3. 如需 Autotools 构建，需要修改 configure/config.status 使用 $TMPDIR