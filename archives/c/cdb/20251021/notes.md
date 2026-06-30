# cdb 20251021 适配笔记

## 编译环境
- 构建系统: custom (DJB build system)
- 编译日期: 2026-06-30
- 编译器: clang/clang++
- 状态: built

## 编译步骤

cdb 使用 D.J. Bernstein 的自定义构建系统（非 autotools）：
1. 设置 conf-cc: `echo "clang -O2" > conf-cc`
2. 设置 conf-ld: `echo "clang -static" > conf-ld`（R26 静态链接）
3. 设置 conf-home: 指向安装路径
4. `make -j1` — 构建所有 cdb 工具
5. 手动复制二进制到 $TEST_PREFIX/bin/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | cr.yp.to HTTPS证书不被信任 | 使用 HTTP 协议下载: http://cr.yp.to/cdb/cdb-0.75.tar.gz |
| 2 | `errno` undefined symbol | error.h 中 `extern int errno;` 在现代系统上无效 | 替换为 `#include <errno.h>` |
| 3 | Conan G1 失败 | 缺少 export_sources() 和 apply_conandata_patches() | 添加这两个方法到 conanfile.py |
| 4 | Conan G2 test_package 失败 | cdbmake 不在 PATH 中 | 使用 self.dependencies 获取完整路径 |
| 5 | Conan test "bad format" | cdbmake 输入缺少终止空行 | 使用 printf 生成正确的输入格式 |

## 源码修改

1. error.h: `extern int errno;` → `#include <errno.h>`（现代系统 errno 修复）
2. conf-cc: `gcc -O2` → `clang -O2`
3. conf-ld: `gcc -s` → `clang -static`（R26 静态链接）
4. conf-home: `/usr/local` → 安装路径

## 依赖版本

无依赖（cdb 是自包含的 C 库）

## 验证结果

- rts 测试套件: 全部通过（exit 0）
  - cdbmake/cdbget/cdbdump/cdbstats/cdbtest 功能验证通过
  - random.cdb 测试通过
  - testzero 测试通过
  - 仅 softlimit/csh 相关环境测试跳过（工具缺失）
- conan-verify: 8道门禁全部通过（G0-G4 + L2/L4/L5）
- 静态链接: 所有二进制为 ELF 64-bit arm64 static

## 注意事项

- cdb 使用 DJB 自定义构建系统，不是 autotools
- conanfile.py 使用 replace_in_file 在 build() 中应用 error.h 修复
- test_package 使用 printf 生成正确格式的 cdbmake 输入
- 4个补丁文件已生成到 patches/ 目录用于审计
---

**编译结束**: 2026-06-30 18:01
**最终状态**: built
