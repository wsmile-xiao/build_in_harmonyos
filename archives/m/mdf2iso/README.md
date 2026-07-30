# mdf2iso

**版本**: 0.3.1
**描述**: Tool to convert MDF (Alcohol 120% images) images to ISO images
**官网**: https://www.nongnu.org/mdf2iso/
**源码**: https://salsa.debian.org/debian/mdf2iso

## 功能

mdf2iso 是一个将 Alcohol 120% 的 MDF 镜像文件转换为标准 ISO 镜像的工具。

## 鸿蒙适配说明

### 编译依赖

- 无外部依赖
- 构建系统：autotools

### 特殊处理

1. **链接器问题**: OHOS SDK 的 lld 链接器依赖 libxml2，需使用 GNU ld（-fuse-ld=bfd）
2. **configure 补丁**: 需修改 configure 的 umask 077 → umask 022（解决 HMDFS 权限问题）
3. **--host 参数**: 使用 --host=aarch64-linux-ohos 绕过 conftest 执行问题（简单软件可用）

### 编译命令

```bash
# 应用补丁
cd mdf2iso-0.3.1
patch -p1 < archives/m/mdf2iso/0.3.1/patches/0001-configure-umask.patch

# 配置（使用 GNU ld）
./configure --prefix=$DEFAULT_PREFIX --host=aarch64-linux-ohos \
  LDFLAGS="-L$DEFAULT_PREFIX/lib -fuse-ld=bfd"

# 编译和安装
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 使用示例

```bash
# 转换 MDF 到 ISO
mdf2iso image.mdf output.iso

# 查看版本
mdf2iso --help
```

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|---------|-------|
| 0.3.1 | published | 2026-06-04 | 1 |

## 相关链接

- [Savannah 项目页](https://savannah.nongnu.org/projects/mdf2iso/)
- [Debian 软件包](https://packages.debian.org/mdf2iso)
