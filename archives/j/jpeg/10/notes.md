# jpeg 10 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-22
- 编译器: clang
- 状态: published

## 编译步骤
```bash
./configure --prefix=$HOME/usr/local
make -j$(nproc)
make check
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 缺少 __OHOS__ 检测分支 | 补丁 0001: E007 平台识别 |
| 2 | config.status 临时文件权限错误 | HMDFS 不支持 mktemp | 修改 config.status 强制使用 $TMPDIR |

## 源码修改
- 0001-config.guess.patch: 添加 HarmonyOS 检测分支
- 0002-config.sub.patch: 添加 ohos-linux 三元组支持

## 验证结果
- make check: 13/13 测试通过 (100%)
- cjpeg -version = Independent JPEG Group's CJPEG, version 10

## 交付物
- cjpeg, djpeg, jpegtran, rdjpgcom, wrjpgcom
- libjpeg.so.10.0.0, libjpeg.a
- jconfig.h, jerror.h, jmorecfg.h, jpeglib.h

## 注意事项
- HMDFS 上 config.status 需要修改临时目录路径
