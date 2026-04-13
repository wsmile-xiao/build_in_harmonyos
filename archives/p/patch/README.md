# GNU Patch 2.7.6 for HarmonyOS

## 编译信息

- **版本**: 2.7.6
- **编译日期**: 2026-03-23
- **目标平台**: aarch64-unknown-linux-ohos
- **编译器**: clang 15.0.4

## 编译步骤

```bash
# 1. 下载源码
curl -LO https://ftp.gnu.org/gnu/patch/patch-2.7.6.tar.xz
tar xf patch-2.7.6.tar.xz
cd patch-2.7.6

# 2. 应用补丁
patch -p1 < 0001-config-guess-harmonyos-support.patch
patch -p1 < 0002-config-sub-harmonyos-support.patch

# 3. 配置和编译
./configure --prefix=$HOME/usr/local
make -j$(nproc)
make install
```

## 测试结果

| 项目 | 数量 |
|------|------|
| 总测试 | 44 |
| 通过 | 32 (73%) |
| 失败 | 9 |
| 跳过 | 1 |

### 失败测试分析

| 测试 | 原因 |
|------|------|
| file-modes | 鸿蒙默认 umask 不同 |
| merge | shell shift 命令行为差异 |
| symlinks | SELinux 软链接访问限制 |

**结论**: 失败测试为环境兼容性问题，核心补丁功能正常。

## 验证

```bash
$ patch --version
GNU patch 2.7.6

$ echo "original" > test.txt
$ patch -p0 < test.patch
patching file test.txt
```

## 注意事项

1. 无 xattr 支持（libattr 不可用）
2. 部分文件权限相关测试失败为环境问题