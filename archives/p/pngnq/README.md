# pngnq — PNG NeuQuant 图像量化工具

pngnq 是一个将 32 位 RGBA PNG 图像量化为 8 位调色板（索引色）PNG 的小型命令行工具，采用 Anthony Dekker 的 NeuQuant 神经网络量化算法。相比中位切分等传统算法，NeuQuant 在视觉质量上通常更优。由 Stuart Coyle 基于 Greg Roelofs 的 pngquant 改写而成。

## 功能概述

- `pngnq`：核心量化工具，将 RGBA PNG 量化为调色板 PNG
  - `-n colours`：目标色彩数（2-256，默认 256）
  - `-s sample factor`：NeuQuant 采样因子
  - `-Q f|n`：抖动算法（Floyd-Steinberg / 无，默认无）
  - `-e extension`：输出文件扩展名（默认 -nq8.png）
  - `-d dir`：输出目录
  - `-f`：强制覆盖已存在文件
  - `-v`：详细输出，`-V`：版本信息
- `pngcomp`：图像对比工具，计算两幅 PNG 图像的块级色彩误差统计（百分比正确像素、平均/最大块误差、标准差）

## OHOS 适配要点

- **构建系统**：autotools（2010 年 Autoconf 2.65 时代 configure）
- **libpng-config 依赖**：`src/Makefile.am` 用反引号调用 `libpng-config` 获取编译/链接参数，conan 打包的 libpng-config 内 `prefix="/"` 输出无效路径，配方 build() 中生成指向 conan 依赖包的 wrapper 脚本并前置 PATH
- **zlib 头文件**：libpng ≥1.5 的 png.h 不再内嵌 zlib.h，`src/rwpng.c` 需补 `#include <zlib.h>` 与 `#include <string.h>`（补丁固化）
- **HMDFS setgid**：configure 内 `umask 077` 与 HMDFS setgid 目录权限冲突（知识条目 E129），补丁改为 `umask 022`
- **无 getopt 依赖**：系统有 getopt，freegetopt 子目录不参与构建

## 依赖关系

### 编译依赖
- libpng 1.6.39（conan 制品仓，静态链接）
- zlib 1.3.1（libpng 传递依赖，conan 制品仓，静态链接）

### 运行依赖
- libc.so（系统 libc；libpng/zlib 静态链接进二进制，无额外运行时库依赖）

## 上游

- 官网：https://pngnq.sourceforge.net/
- 源码：https://downloads.sourceforge.net/project/pngnq/pngnq/1.1/pngnq-1.1.tar.gz
- 许可证：Libpng（Greg Roelofs "PNG: The Definitive Guide" 风格 BSD 类许可 + NeuQuant 许可，见 COPYING）
- 上游 1.1（2011）后停更，无测试套件（test_package 以真实量化测试补偿）
