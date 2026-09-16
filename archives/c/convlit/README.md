# convlit

ConvertLIT：将 Microsoft Reader .LIT 电子书转换为 OEBPS/HTML 的 CLI 工具（原 clit）。

## 上游信息
- 上游: https://www.kyzer.me.uk/pack/convlit/
- 作者: Dan A. Jackson (Digital Rights Software)
- 协议: GPL-2.0-or-later
- 源码包: convlit_1.8.orig.tar.gz（与上游 open_c-lit-1.8.tar.gz 字节一致）

## OHOS 适配
- Makefile 构建；依赖 libtommath/1.3.0（ohpcd conan 包）。
- 上游 Makefile 写死 gcc 与 ../libtommath-0.30 路径，已 patch 为 $(CC)/$(AR) + -ltommath。
- 源码 CRLF 统一为 LF 后打补丁；补充缺失头文件。
- 产物：`clit` 可执行文件（版本/使用说明冒烟）。

## 依赖
| 依赖 | 版本 | 说明 |
|------|------|------|
| libtommath | 1.3.0 | 大整数运算（DRM5 私钥解密） |
