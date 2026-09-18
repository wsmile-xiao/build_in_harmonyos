# libmwaw-tools

## 软件描述

libmwaw 是一个解析旧版 Mac 文本文档（macOS X 之前格式）的 C++ 库，libmwaw-tools
是其构建产物中的命令行转换工具集：

- **mwaw2text**: 转换为纯文本
- **mwaw2csv**: 转换为 CSV（表格类文档）
- **mwaw2html**: 转换为 HTML
- **mwaw2raw**: 输出原始解析结构
- **mwaw2svg**: 转换为 SVG
- **mwawFile**: 识别 Mac 文档类型/格式
- **mwawZip**: Mac 文档打包/解包

支持文档格式：MacWrite、ClarisWorks、Microsoft Word (Mac)、StarOffice (Mac)、
FrameMaker、OfficeWorks、OpenOffice/WordPerfect 等数十种 legacy 格式。

## 版本信息

- 当前版本: 0.3.22
- 官方主页: https://sourceforge.net/projects/libmwaw/

## OHOS 适配

- 构建系统为 Autotools（configure + make），`--with-docs=no` 禁用 doxygen 文档构建
- 三个移植补丁：config.guess/config.sub 增加 HarmonyOS 识别，configure umask 兼容 HMDFS
- 关键坑：依赖包 librevenge 发布的 `.pc`/`.la` 文件 prefix 硬编码为 `/`（系统安装布局），
  在 conan 包布局下 pkg-config 与 libtool 都会读错路径。解法是在配方 build() 内
  staging 纯 `.a` 副本 + 本地生成正确 prefix 的 `.pc`，`PKG_CONFIG_PATH` 指向 staging 目录
- `package_type = "application"`（工具包 + 附带 libmwaw 库）

## 依赖说明

编译/运行依赖：
- librevenge 0.0.5（文档解析底层库）
- zlib 1.3.1（压缩流）

libmwaw-0.3.so 将 librevenge/zlib 静态链接，运行时仅依赖 libc++_shared.so 和 libc.so。

## 功能验证（0.3.22, aarch64/OHOS）

| 功能 | 状态 |
|------|------|
| mwawFile --version → 0.3.22 | ✅ 通过 |
| mwaw2text --version → 0.3.22 | ✅ 通过 |
| C++ API: MWAWDocument::isFileFormatSupported() | ✅ 通过（非 Mac 载荷/空流正确拒绝） |
| conan-verify G0-G4 | ✅ 全 PASS |

## 参考资料

- 源码: https://sourceforge.net/projects/libmwaw/
- 本项目 conan 配方: archives/l/libmwaw-tools/0.3.22/conanfile.py
