# figlet — OpenHarmony PC 适配

## 基本信息
- 软件: figlet
- 版本: 2.2.5
- 描述: FIGlet 是一个将普通文本转换为大号 ASCII 艺术字的命令行工具
- 构建系统: Makefile (plain make, no configure)
- 目标平台: ohos-aarch64
- 上游: https://www.figlet.org/

## 编译指导
- 编译器: clang (需覆盖 Makefile 默认的 gcc)
- CC 和 LD 均需设为 clang
- XCFLAGS=-DTLF_FONTS 启用 TLF 字体支持
- CFLAGS=-fPIC -O2 -Wall
- DEFAULTFONTDIR 和 DEFAULTFONTFILE 在编译时硬编码

## 补丁清单
- patches/0001-utf8.h.patch: 添加 `#include <sys/cdefs.h>` 解决 `__BEGIN_DECLS`/`__END_DECLS` 宏在 OHOS/clang 下未定义的问题

## 已知限制
- 22 个 K&R 风格函数定义弃用警告 (不影响功能)
- 字体路径编译时硬编码，运行时需确保路径一致

## 功能验证
- `figlet -I 1` → 20205 (版本信息正确)
- `figlet Hello` → ASCII 艺术输出正常
- `figlet -f slant Test` → 字体切换正常
- `chkfont standard.flf` → 0 errors, 0 warnings
- `make check` → 26/26 测试全部通过
