# openttd-opengfx 8.0 测试报告

## 编译测试

**状态**: partial (预构建包安装)

**说明**: OpenGFX 是 OpenTTD 的数据/图形包，不是传统的可编译 C/C++ 软件。从源码编译需要：
- nmlc (NML compiler) - ✅ 已安装 Python nml 0.9.0
- grfid (来自 grfcodec) - ❌ 无法编译（grfcodec 需要 Boost 库）
- gcc/cc 用于 pnml 预处理 - ✅ clang 可替代

由于 PIL (Pillow) 的 .so 扩展模块在 HMDFS 上无法加载（Permission denied，即使签名后），无法从源码编译 .grf 文件。
因此，使用官方预构建发布包 (opengfx-8.0-all.zip) 进行安装。

## 安装验证

### Staging 验证 (DESTDIR 模式)
- 安装路径: $TEST_PREFIX/$DEFAULT_PREFIX/share/openttd/baseset/opengfx
- GRF 文件: 6/6 ✅
- OBG 文件: 1/1 ✅
- 文档文件: 3/3 ✅

### make check
- 状态: SKIPPED (grfid 不可用)
- 原因: grfcodec/grfid 未安装，无法执行 checksum 验证

## 文件清单

| 文件 | 大小 |
|------|------|
| ogfx1_base.grf | 2.7 MB |
| ogfxc_arctic.grf | 287 KB |
| ogfxe_extra.grf | 988 KB |
| ogfxh_tropical.grf | 472 KB |
| ogfxi_logos.grf | 250 KB |
| ogfxt_toyland.grf | 622 KB |
| opengfx.obg | 10.7 KB |
| changelog.txt | 26.8 KB |
| license.txt | 18.1 KB |
| readme.txt | 15.1 KB |
