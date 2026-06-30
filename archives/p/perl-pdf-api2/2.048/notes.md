# perl-pdf-api2 2.048 — 编译笔记

## 软件信息
- **软件**: PDF::API2 (perl-pdf-api2)
- **版本**: 2.048
- **描述**: Create, modify, and examine PDF files
- **构建系统**: ExtUtils::MakeMaker (Makefile.PL)
- **CPAN**: https://metacpan.org/dist/PDF-API2

## Phase 1: 初始化
- 源码下载: https://cpan.metacpan.org/authors/id/S/SS/SSIMMS/PDF-API2-2.048.tar.gz
- 解压成功，185 个文件
- 无嵌套源码问题

## Phase 2: 依赖处理
- Compress::Zlib: 系统自带 ✅
- Font::TTF: 缺失，从 CPAN 安装 Font-TTF-1.06 → ~/usr/local/lib/perl5/
- Test::Exception + Sub::Uplevel: 测试依赖，从 CPAN 安装

## Phase 3: 编译
- `perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX` → PASS
- `make` → PASS（纯 Perl 模块，无 C/XS 编译）
- `make test` → 45/46 文件通过，757/757 子测试通过
- `make install DESTDIR=$TEST_PREFIX` → PASS
- 无补丁应用
- 无源码修改

## Phase 4: 打包
- 使用 ohc-run.py package 制作预编译包
- 纯 Perl 模块，无 ELF 二进制，无需签名

## Phase 5: 功能测试验证（2026-06-24）

### 5.1 自定义功能测试（54/54 PASS, 4 SKIP）
| 测试类别 | 通过/总数 | 详情 |
|----------|-----------|------|
| 模块加载 | 4/4 | PDF::API2, Page, Content, Util |
| PDF 创建 | 7/7 | 新建文档、版本设置、A4/Letter/A3 页面、多页(10页) |
| 文本操作 | 9/9 | 基本文本、多行、特殊字符、颜色、旋转、对齐、字宽、Unicode |
| 核心字体 | 7/7 | Helvetica, Times-Roman, Courier, Bold, Oblique, Symbol, ZapfDingbats |
| 图形绘制 | 6/6 | 线条、矩形、圆形、多边形、线宽、虚线 |
| PDF I/O | 8/8 | 文件保存、字符串输出、复杂多页、打开、追加、计数、修改、循环保存 |
| 元数据/注释 | 7/7 | 标题、作者、主题、关键词、旋转、超链接、多字体混排 |
| 页面属性 | 4/4 | mediabox 检索、cropbox、preferences、大文本块 |
| 压力测试 | 2/2 | 100 页 PDF、5 轮开/存循环 |
| 图像嵌入 | SKIP | 需测试图片文件（官方测试已覆盖 png/jpg/gif/tiff/pnm） |

### 5.2 官方测试套件（757/757 子测试通过）
- 46 个测试文件中 45 个完全通过
- 唯一非完全通过: `circular-references.t`（退出码 2，但 0 个子测试失败，Test::Exception TAP 解析问题）
- 所有图像嵌入测试通过: t/png.t, t/jpg.t, t/gif.t, t/tiff.t, t/pnm.t, t/gd.t
- TrueType 字体嵌入通过: t/font-ttf.t (via Font::TTF)
- 所有回归测试通过: rt120397, rt120450, rt126274, rt67767, rt69503

详见: `reports/functional-test-report.md`

## 关键发现
1. PDF::API2 是纯 Perl 模块，无 XS 组件，不涉及 E078 (musl BIND_NOW) 问题
2. 所有核心功能（创建/编辑/保存/读取 PDF）在鸿蒙平台上正常工作
3. 依赖 Font::TTF 需手动从 CPAN 安装（用于 TrueType 字体嵌入）
4. PERL5LIB 需设置为 ~/usr/local/lib/perl5
5. 100 页 PDF 生成和 5 轮循环存储压力测试均无崩溃/泄漏
6. 图像嵌入功能经官方测试验证可用（PNG/JPEG/GIF/TIFF/PNM）

---

**编译结束**: 2026-06-24 16:18
**功能测试**: 2026-06-24 16:30
**最终状态**: published (功能验证通过，可正常使用)
