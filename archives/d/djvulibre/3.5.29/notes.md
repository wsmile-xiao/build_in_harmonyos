# djvulibre 3.5.29 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `python3 $SKILL_ROOT/scripts/ohc-run.py init-build djvulibre 3.5.29 --url https://sourceforge.net/projects/djvu/files/DjVuLibre/3.5.29/djvulibre-3.5.29.tar.gz/download`
2. `cd $BUILD_SRC_DIR && source .build-context-djvulibre-3.5.29`
3. `./configure --prefix=$DEFAULT_PREFIX --disable-desktopfiles`
4. `make -j1`
5. `make install DESTDIR=$TEST_PREFIX`
6. `make check` (djvulibre没有test suite，所有模块返回Nothing to be done)
7. `python3 $SKILL_ROOT/scripts/ohc-run.py verify-build djvulibre 3.5.29`
8. `python3 $SKILL_ROOT/scripts/ohc-run.py package djvulibre 3.5.29`
9. `make install` (本地安装验证，不带DESTDIR)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make在desktopfiles目录失败 | ImageMagick convert命令无法生成PNG图标（convert: no images defined） | 使用configure选项 `--disable-desktopfiles` 跳过图标生成 |
| 2 | manifest缺少build_system字段 | 初始化生成的manifest模板缺少顶层build_system键 | 手动补充 `build_system: autotools` 到manifest.yaml |

## 源码修改

无源码修改。所有适配通过configure选项完成（`--disable-desktopfiles`）。
configure自动识别 `linux-ohos` 平台，无需修改 config.guess/config.sub。

## 依赖版本

- jpeg (libjpeg): 预编译包
- tiff (libtiff): 预编译包
- zlib: 预编译包

## 验证结果

```bash
# make check
Making check in libdjvu - Nothing to be done for 'check'
Making check in tools - Nothing to be done for 'check'
Making check in share - Nothing to be done for 'check'
Making check in xmltools - Nothing to be done for 'check'

# verify-build: PASS (质量报告)
# packaging: djvulibre-3.5.29-ohos-aarch64.tar.gz (9221KB)
#            djvulibre-3.5.29-ohos-aarch64-debug.tar.gz (2970KB)

# 本地安装验证: 成功
# ls /storage/Users/currentUser/usr/local/lib/libdjvulibre.so.21.8.0
# ls /storage/Users/currentUser/usr/local/bin/ddjvu
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| djvulibre-3.5.29-ohos-aarch64.tar.gz | 9221KB | aarch64 架构制品 |
| djvulibre-3.5.29-ohos-aarch64-debug.tar.gz | 2970KB | aarch64 debug 制品 |

## 注意事项

- Iconv支持检测为no，但不影响核心DjVu功能编译
- configure自动识别平台为 linux-ohos，无需手动修改平台识别
- 编译警告：libtiff的uint16/uint32类型被标记为deprecated，不影响功能
---

**编译结束**: 2026-05-26 10:25
**最终状态**: published
