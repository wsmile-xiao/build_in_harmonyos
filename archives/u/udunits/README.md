# udunits

**描述**: UDUNITS-2 物理量单位转换库及命令行工具，提供单位解析、换算、派生单位定义，被 CMOR 等气候模型工具链依赖。

物理量单位库：支持长度、质量、时间、温度、压力等单位的解析与换算，内置 XML 单位数据库。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.2.28.1 | built (conan 配方适配，构建+测试通过) | CMOR 3.15.2 依赖链必需 |

## 版本索引

| 版本 | 日期 | 状态 |
|------|------|------|
| 2.2.28.1 | 2026-09-09 | built (conan 配方适配) |

## 依赖

- expat >= 2.8（XML 单位数据库解析，硬依赖）

## 鸿蒙适配

- **构建系统**: autotools + libtool；release tarball 无预生成 configure，配方内以
  libtoolize → aclocal → autoconf → autoheader → automake 显式重建生成文件（R6）
- **工具链**: autoconf/2.72 automake/1.18 libtool/2.5.4（tool_requires）
- **perl 处理**: Conan perl 包 XS 模块无法在 HMDFS dlopen，bootstrap 使用原生
  perl + PERL5LIB 限定 automake share（ding-libs 0.7.0 同款方案）
- **E129**: configure/config.status 临时目录 umask 077 → 022
- **PWD 修复**: HMDFS getcwd 失效，发布逻辑 PWD 供 wrapper 路径推算

## 功能验证

- 上游 make check：lib 目录 0 用例（CUNIT 未检测）+ prog udunits2 smoke test
- test_package 自研 20 项 C API 断言（14 CHECK + 6 near_eq）全部通过（XML 加载/单位查找/转换/温度/拒绝）
