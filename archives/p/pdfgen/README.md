# PDFGen

PDFGen 是一个用于创建 PDF 文件的简易 C 库（AndreRenaud/PDFGen，public domain / Unlicense）。整个库就是 pdfgen.c + pdfgen.h 两个文件，零外部依赖，API 覆盖页面、文本（含 UTF-8 与换行对齐）、几何图形（线/贝塞尔/圆/椭圆/多边形）、条形码（Code39/Code128）、书签、位图嵌入（JPEG/PNG/BMP/PPM/RGB24）等。

## 功能概述
- 单翻译单元 C 库：无构建系统依赖，编译 pdfgen.c 即可
- 页面与书签：多页文档、层级书签、A4/A3/自定义页面尺寸
- 文本：内置 14 种 PDF 标准字体、UTF-8 特殊字符、自动换行与两端对齐
- 图形：线段/三次贝塞尔/二次贝塞尔/圆/椭圆/矩形/多边形（描边+填充、透明度）
- 条形码：Code 39 / Code 128A
- 图像：JPEG/PNG/BMP/PPM 文件嵌入 + RGB/RGB24/灰色原始数据
- 零依赖、public domain（Unlicense）

## OHOS 适配
- 配方直接编译 pdfgen.c 归档 libpdfgen.a（静态库，叶子库）
- 上游 tag 为 0.1.0（无 v 前缀）
- 上游测试：testprog（全 API 功能程序）设备实测 exit 0；tests.sh 断言用 pypdf 等价重表达 7/8 过（valgrind leg 工具缺失豁免）
- test_package 消费者链路：pdfgen::pdfgen 编译 → 全 API 测试程序 → pypdf 校验生成 PDF 结构

## 依赖关系
- **编译依赖**: 无
- **运行依赖**: 无

## 参考资料
- 官网: https://github.com/AndreRenaud/PDFGen
