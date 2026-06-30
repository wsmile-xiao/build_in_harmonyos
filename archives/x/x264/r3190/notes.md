# x264 r3190 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-20
- 编译器: clang
- 状态: published

## 编译步骤

1. 下载源码
   ```bash
   curl -L -o x264-r3190.tar.gz "https://code.videolan.org/videolan/x264/-/archive/r3190/x264-r3190.tar.gz"
   tar -xzf x264-r3190.tar.gz
   cd x264-r3190
   ```

2. Configure
   ```bash
   export CC=clang
   ./configure --prefix=~/usr/local --enable-shared --enable-static --enable-pic
   ```

3. 编译安装
   ```bash
   make -j4
   make install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 缺少 HarmonyOS 平台检测 | 添加 HarmonyOS case 分支 |
| 2 | configure shebang 错误 | #!/bin/bash 不存在 | 修正为 /data/service/hnp/bin/bash |

## 验证结果

```bash
pkg-config --modversion x264
# 输出: 0.165.x
```

---
**编译结束**: 2026-05-20 17:17
**最终状态**: published