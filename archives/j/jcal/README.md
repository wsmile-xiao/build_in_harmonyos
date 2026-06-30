# jcal

Jalali（波斯/伊朗）日历库及终端工具，提供 jcal 日历显示和 jdate 日期格式化命令行工具，以及 libjalali C 库。

## 功能概述

- **jcal**: 显示 Jalali 日历，支持单月、全年、前三月、儒略日等模式
- **jdate**: Jalali 日期格式化工具，类似 date 命令，支持 Jalali↔Gregorian 互转
- **libjalali**: C 库，提供 Jalali 日历转换、时间操作等 API（jalali_get_date, jlocaltime_r, jstrftime 等）

## OHOS 适配

- 构建系统: autotools，源码包不含 configure 脚本，需先运行 autoreconf
- 源码包无顶层目录（strip_root=False）
- configure.in 需添加 AC_CONFIG_AUX_DIR([.]) 避免 libtoolize 辅助文件放置错误
- 终端工具静态链接（R26）: --disable-shared --enable-static + LDFLAGS=-static
- 无外部依赖

## 依赖关系

- 编译依赖: 无
- 运行依赖: musl libc（静态链接后仅依赖 libc.so）

## 参考资料

- 官网: https://nongnu.org/jcal
- 源码: https://download.savannah.gnu.org/releases/jcal/
- 项目: https://savannah.nongnu.org/projects/jcal/