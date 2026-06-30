# chafa 1.18.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: published
- 平台: aarch64-unknown-linux-ohos

## 编译步骤

1. 下载源码：从 hpjansson.org/chafa/releases 下载官方tarball（包含configure脚本）
2. 应用补丁：使用 patch-autotools-ohos.pl 添加 HarmonyOS 平台识别
3. 配置：`./configure --prefix=$DEFAULT_PREFIX --without-tools`
   - `--without-tools`: 跳过命令行工具构建，避免 freetype2 依赖
4. 编译：`make -j2`
5. 安装：`make install DESTDIR=$TEST_PREFIX`
6. 打包：生成预编译包 chafa-1.18.2-ohos-aarch64.tar.gz

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 __OHOS__ 检测 | 使用 patch-autotools-ohos.pl 添加 HarmonyOS 支持 |
| 2 | config.status 临时文件创建失败 | HMDFS 文件系统权限限制，mktemp 创建的目录无法写入 | 修改 config.status 使用固定临时目录 $TMPDIR/chafa-config-workdir |
| 3 | 缺少 freetype2 依赖 | 命令行工具需要 freetype2 | 使用 --without-tools 跳过工具构建 |

## 源码修改

| 补丁文件 | 修改内容 |
|----------|----------|
| 0001-config.guess.patch | 添加 __OHOS__ LIBC 检测和 HarmonyOS 系统识别分支 |
| 0002-config.sub.patch | 添加 ohos-linux 三元组支持 |

## 依赖版本

| 软件 | 版本 |
|------|------|
| glib | 2.88.0 |
| pcre2 | 10.40 |

## 验证结果

```bash
# 制品文件检查
ls -lh archives/c/chafa/1.18.2/packaging/
# chafa-1.18.2-ohos-aarch64.tar.gz      3.4M
# chafa-1.18.2-ohos-aarch64-debug.tar.gz 225K

# 制品内容验证
tar -tzf chafa-1.18.2-ohos-aarch64.tar.gz
# include/chafa/*.h (13个头文件)
# lib/libchafa.so.0.11.2
# lib/libchafa.a
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| chafa-1.18.2-ohos-aarch64.tar.gz | 3.4M | 主包（头文件+库文件） |
| chafa-1.18.2-ohos-aarch64-debug.tar.gz | 225K | 调试符号包 |

## 注意事项

1. **HMDFS 权限限制**：config.status 脚本在 HMDFS 文件系统上无法在 mktemp 创建的临时目录中写入文件，需要手动修改使用固定目录
2. **--without-tools**：如果需要构建命令行工具，需要先安装 freetype2
