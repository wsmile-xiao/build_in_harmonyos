# exiftool 13.50 — OpenHarmony 编译记录

## 基本信息
- 软件: exiftool (Image-ExifTool)
- 版本: 13.50
- 描述: Perl 库和命令行工具，用于读写 EXIF、GPS、IPTC、XMP 等图像/音频/视频元数据
- 构建系统: Perl MakeMaker (ExtUtils::MakeMaker)
- 目标平台: ohos-aarch64
- 源码 URL: https://sourceforge.net/projects/exiftool/files/Image-ExifTool-13.50.tar.gz/download

## 编译指导

### Perl 模块编译流程
```bash
# 1. 解压源码
tar xzf Image-ExifTool-13.50.tar.gz
cd Image-ExifTool-13.50

# 2. 生成 Makefile（Perl 模块使用 perl Makefile.PL 代替 configure）
perl Makefile.PL PREFIX=$HOME/usr/local

# 3. 编译
make

# 4. 安装到 staging 目录（DESTDIR 模式）
make install DESTDIR=$HOME/test-install-exiftool-13.50

# 5. 测试
make test  # 113 个测试文件，600 个断言，全部 PASS

# 6. 打包（需要复制模块到 bin/lib）
mkdir -p $HOME/test-install-exiftool-13.50/$HOME/usr/local/bin/lib
cp -r $HOME/test-install-exiftool-13.50/$HOME/usr/local/lib/site_perl/*/Image \
      $HOME/test-install-exiftool-13.50/$HOME/usr/local/bin/lib/
cp -r $HOME/test-install-exiftool-13.50/$HOME/usr/local/lib/site_perl/*/File \
      $HOME/test-install-exiftool-13.50/$HOME/usr/local/bin/lib/
```

### 关键参数
- `PREFIX=$HOME/usr/local` - 安装前缀（运行时路径）
- `DESTDIR=...` - staging 目录（打包用）
- 无需 `--build/--host` 参数（native 编译，非交叉编译）

## 补丁清单

本次编译无补丁。源码无需修改即可在 HarmonyOS 上编译运行。

## 已知限制

### Perl 模块路径问题
1. **问题描述**: Perl 模块安装路径（`lib/site_perl/`）与系统 Perl @INC 可能不匹配
2. **解决方案**: exiftool 在 BEGIN 块中会自动添加 `bin/lib` 到 @INC，将模块复制到 `bin/lib/Image/` 和 `bin/lib/File/`
3. **打包结构**:
   ```
   bin/exiftool          ← 主脚本
   bin/lib/Image/ExifTool/ ← Perl 模块（200+ 文件）
   bin/lib/File/RandomAccess.pm ← 依赖模块
   lib/site_perl/...     ← 标准路径（兼容）
   ```

### 测试说明
- 测试全部通过（113 文件，600 断言）
- 测试耗时约 37 秒

## 功能验证

### 版本检查
```bash
$ exiftool -ver
13.50
```

### 基础功能测试
```bash
# 查看 JPEG 图片 EXIF 信息
$ exiftool image.jpg

# 查看 GPS 信息
$ exiftool -gps:all image.jpg

# 批量处理目录
$ exiftool -r -datetimeoriginal dir/

# 查看支持的文件类型
$ exiftool -listf
```

### 安装验证
```bash
# 安装预编译包
tar xzf exiftool-13.50-ohos-aarch64.tar.gz -C ~/usr/local
cd exiftool-13.50-ohos-aarch64
sh install-exiftool-13.50.sh

# 验证安装
~/usr/local/bin/exiftool -ver
# 输出: 13.50
```

## 依赖要求

- Perl 5.42.0 或更高版本（HarmonyOS 已预装）
- 无其他依赖

## 文件支持范围

exiftool 支持读取/写入以下格式的元数据：
- 图像: JPEG, PNG, GIF, TIFF, RAW (CR2, NEF, DNG 等), HEIC, AVIF 等
- 视频: MP4, MOV, AVI, M2TS 等
- 音频: MP3, FLAC, AAC 等
- 文档: PDF, OOXML 等
- 其他: ZIP, JSON, HTML 等

完整支持列表: https://exiftool.org/
