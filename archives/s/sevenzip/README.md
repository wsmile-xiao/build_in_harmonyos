# sevenzip 26.00 — OpenHarmony 编译记录

## 基本信息
- 软件: sevenzip (7-Zip)
- 版本: 26.00
- 构建系统: 自定义 Makefile（makefile.gcc + cmpl_clang.mak）
- 目标: aarch64-unknown-linux-ohos
- 编译器: clang 15.0.4

## 编译指导

### 构建系统说明
7-Zip 使用自定义的 Makefile 构建系统，不是标准的 autotools 或 cmake。主要构建文件位于：
- `CPP/7zip/Bundles/Alone2/makefile.gcc` - 主构建文件
- `CPP/7zip/cmpl_clang.mak` - Clang 编译配置

### 编译步骤
```bash
# 进入源码目录
cd CPP/7zip/Bundles/Alone2

# 使用 Clang 编译
make -j -f ../../cmpl_clang.mak

# 生成的二进制文件
b/c/7zz
```

### 注意事项
- OpenHarmony Clang 编译器默认启用严格警告 `-Weverything -Wfatal-errors`
- 需要修改 `CPP/7zip/warn_clang.mak`，添加必要的 `-Wno-*` 选项
- 目标平台是 arm64，使用 clang 15.0.4

## 补丁清单
- `fix-clang-warnings.patch`: 修复 OpenHarmony Clang 编译警告问题
  - 添加 `-Wno-cast-qual`: 允许 const cast（OpenHarmony 系统头文件需要）
  - 添加 `-Wno-shorten-64-to-32`: 允许整数精度转换警告
  - 添加 `-Wno-disabled-macro-expansion`: 允许递归宏展开（OpenHarmony stdio.h）

## 已知限制
- 当前仅编译了命令行版本 `7zz`（支持所有格式）
- 未编译 GUI 版本和文件管理器版本
- RAR 解压功能保留（包含 unRAR 许可限制）

## 功能验证

### 基本测试
```bash
# 创建测试文件
echo "test content" > test.txt

# 压缩
7zz a test.7z test.txt

# 解压
7zz x test.7z -ooutput/

# 验证
cat output/test.txt
```

### 性能测试
```bash
# 基准测试
7zz b
```

### 支持格式
7zz 支持所有常见压缩格式：
- 7z, ZIP, GZIP, BZIP2, TAR
- XZ, WIM, ARJ, CAB, CHM
- CPIO, CramFS, DMG, EXT
- FAT, GPT, HFS, ISO, LZH
- LZMA, MBR, MSI, NSIS, NTFS
- RAR, RPM, SquashFS, UDF
- VHD, VHDx, VMDK, XAR, Z
- 等等...
