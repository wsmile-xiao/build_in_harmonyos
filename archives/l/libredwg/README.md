# GNU LibreDWG

GNU LibreDWG是读写DWG文件（AutoCAD原生格式）的C库，附带dwgread/dwgwrite/dwg2dxf等命令行工具。

## 功能概述
- 读取r13-r2018各版本DWG，写入r13-r2000 DWG及多版本DXF
- 转换JSON/DXF/DXFB/SVG等格式，含dwggrep/dwglayers等工具
- 提供dwg.h/dwg_api.h C API（-lredwg -lm链接）

## OHOS适配要点
- Autotools原生构建，--build三元组兼容config.guess
- --disable-bindings/--disable-docs/--disable-python裁掉缺失依赖
- --disable-werror兼容新版clang警告
- 上游make check量大：unit-testing数百用例+programs集成套件

## 依赖关系
- 运行时无第三方依赖，仅需libm
- 构建依赖系统autotools/clang

## 参考资料
- [GNU官网](https://www.gnu.org/software/libredwg/)
- [源码镜像](https://github.com/LibreDWG/libredwg)
- [FTP归档](https://ftp.gnu.org/gnu/libredwg/)
