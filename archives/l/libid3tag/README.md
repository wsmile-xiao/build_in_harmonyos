# libid3tag

## 简介

libid3tag 是一个 C 语言库，用于解析和操作 ID3 标签——MP3 音频文件中使用的元数据格式。它支持 ID3v1（简单的 128 字节尾部格式）和 ID3v2（更灵活、可扩展的头部格式）。

## 功能概述

- **ID3v2 标签读写**：创建、修改、删除 ID3v2 标签帧（标题、艺术家、专辑等）
- **ID3v1 标签支持**：兼容 ID3v1/ID3v1.1 简单标签格式
- **文件接口**：直接打开 MP3 文件进行标签操作（`id3_file_open` / `id3_file_update`）
- **原始字节解析**：支持从内存中的原始数据解析标签（`id3_tag_parse` / `id3_tag_render`）
- **字符编码转换**：支持 ISO-8859-1、UTF-16、UTF-16BE、UTF-8 等编码
- **流派（genre）数据库**：内置 ID3 标准流派名称索引

## OHOS 适配

### 适配要点

- CMake 4.x 与项目的 `cmake_minimum_required(3.1)` 不兼容，编译时需添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
- Savannah 官方下载源在 OHOS 环境不可达（SSL/超时问题），需使用 Debian pool mirror (`ftp.debian.org`) 替代
- `init-build` 依赖 `configure.ac` 判断构建系统，纯 CMake 项目需手动修正 `build_system` 字段
- G0 clean-verify 仅支持 autotools，CMake 项目需创建 `hints/configure.sh` wrapper

### 已知问题

- 编译过程中有指针类型警告（`char` / `unsigned char` 混用），不影响功能
- 源码包不含测试套件（`ctest` 报告"No tests were found"）

## 依赖

- **zlib** (必须) — ID3v2 标签中压缩帧的解压缩依赖

## 功能验证

### 上游测试

上游 tarball 不含测试套件（`ctest` 报告 "No tests were found"），官方 CI 仅执行 configure/build/install。**上游无正式测试**。

### test_package (Conan 消费者测试)

`test_package/` 真实调用安装后的 libid3tag API，覆盖完整读写闭环（18 项断言，全部 PASS）：
- 库版本号验证 ✅
- ID3v2 标签创建与 TIT2 帧挂载 ✅
- UTF-8 编码设置与 UCS-4 字符串添加 ✅
- 两遍 render（长度查询 + 写入）✅
- query/parse 回读 ✅
- findframe 检索与 UTF-8 duplicate 比对 ✅
- ID3 magic 校验 ✅

另有版本级 `reports/test-report.md`（早期 9 项测试、67 断言记录）。

## 参考

- 源码下载: https://ftp.debian.org/debian/pool/main/libi/libid3tag/
- 许可证: GPL v2+