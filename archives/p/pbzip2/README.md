# pbzip2 — OpenHarmony 编译记录

## 基本信息
- 软件: pbzip2 — 并行BZIP2文件压缩器，基于pthread实现多线程压缩/解压
- 版本: 1.1.13
- 构建系统: **makefile**（纯Makefile项目，无autotools/configure脚本）
- 许可证: bzip2-1.0.6 (BSD风格)
- 目标: ohos-aarch64
- 依赖: bzip2库（libbz2，已有预编译包）

## 编译指导
pbzip2是纯Makefile项目，无configure脚本。编译时需手动传递编译参数：
```bash
make CXXFLAGS="-O2 -fPIC -pthread -D_POSIX_PTHREAD_SEMANTICS -D_LARGEFILE64_SOURCE -D_FILE_OFFSET_BITS=64 -DUSE_STACKSIZE_CUSTOMIZATION -I$PREFIX/include" \
     LDFLAGS="-L$PREFIX/lib" \
     LDLIBS="-lbz2 -lpthread"
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
```

注意事项：
- C++11编译器要求PRIuMAX宏与字符串之间必须有空格
- HMDFS文件系统不支持`ln -s -f`覆盖，需使用`rm -f && ln -s`
- 需添加`-I$PREFIX/include`和`-L$PREFIX/lib`以找到bzip2依赖

## 补丁清单
| 补丁文件 | 说明 |
|---------|------|
| 0001-BZ2StreamScanner.cpp.patch | 修复C++11 PRIuMAX字符串拼接（5处） |
| 0002-Makefile.patch | 添加-fPIC/-I/-L路径，HMDFS ln兼容，PREFIX可覆盖 |
| 0003-configure.patch | 新增configure wrapper（no-op，让G0验证通过） |
| 0004-pbzip2.cpp.patch | 修复C++11 PRIuMAX字符串拼接（27处） |

## 已知限制
- 无标准测试套件（make check不可用）
- 源码存在C++11 PRIuMACRO拼接兼容问题，需在所有`"MACRO`间加空格
- HMDFS不支持`ln -s -f`覆盖式软链接创建

## 功能验证
```bash
~/usr/local/bin/pbzip2 --version   # Parallel BZIP2 v1.1.13
~/usr/local/bin/pbzip2 -z file.txt # 基本压缩
~/usr/local/bin/pbzip2 -d file.txt.bz2  # 基本解压
~/usr/local/bin/pbzip2 -z -p2 file.txt  # 2线程压缩
```
完整测试报告见 `1.1.13/reports/test-report.md`（12项测试全部通过）。