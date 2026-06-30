# zpaq 7.15 适配笔记

## 编译环境
- 构建系统: makefile（简单 Makefile，非 autotools）
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://mattmahoney.net/dc/zpaq715.zip（zip 格式）
2. 修改 Makefile:
   - `CXX=g++` → `CXX=clang++`（g++ 不可用）
   - `CXXFLAGS=-O3 -march=native` → `CXXFLAGS=-O2 -fPIC`（去掉 march=native，适配 aarch64）
   - `CPPFLAGS+=-Dunix` → `CPPFLAGS+=-Dunix -DNOJIT`（禁用 JIT，避免 Illegal instruction）
   - `PREFIX=/usr/local` → `PREFIX=$DEFAULT_PREFIX`
3. make -j1 编译成功
4. make install DESTDIR=$TEST_PREFIX（staging 安装）
5. make install（本地部署验证）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make 失败：g++ not found | Makefile 默认用 g++，OpenHarmony 环境只有 clang++ | 修改 Makefile CXX=clang++ |
| 2 | zpaq extract 时 "Illegal instruction" (core dump) | zpaq JIT 编译器生成 x86 机器码，aarch64 无法执行 | 添加 -DNOJIT 禁用 JIT |
| 3 | verify-build G4 失败：manifest 缺少 build_system | verify 脚本检查顶层 build_system 字段 | manifest.yaml 添加顶层 build_system: makefile |
| 4 | manifest.yaml tar_format 错误 | init-build 默认设为 tar.gz，但源码是 zip | 修正 tar_format: zip |

## 源码修改

修改文件: Makefile
- CXX: g++ → clang++
- CXXFLAGS: -O3 -march=native → -O2 -fPIC
- CPPFLAGS: 增加 -DNOJIT
- PREFIX: /usr/local → $DEFAULT_PREFIX

无需补丁文件（仅 Makefile 覆盖参数即可）。

## 依赖版本

无外部依赖。

## 验证结果

```bash
# 功能测试 (add + extract + cmp)
./zpaq add archive.zpaq zpaq.cpp → OK
./zpaq extract archive.zpaq zpaq.cpp -to zpaq.cpp.new → OK
cmp zpaq.cpp zpaq.cpp.new → OK (文件一致)

# 本地安装验证
/storage/Users/currentUser/usr/local/bin/zpaq → zpaq v7.15 journaling archiver, compiled Jun 10 2026
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| zpaq-7.15-ohos-aarch64.tar.gz | 413KB | 预编译包（含 zpaq 二进制 + man page） |
| zpaq-7.15-ohos-aarch64-debug.tar.gz | - | 调试符号包 |

## 注意事项

1. **NOJIT 必须启用**：zpaq 的 JIT 生成 x86 机器码，在 ARM/aarch64 上会导致 Illegal instruction。必须用 -DNOJIT 禁用 JIT，使用解释模式（性能略低但功能完整）。
2. **构建系统为 makefile**：zpaq 没有标准 autotools/cmake，使用简单 Makefile，编译参数通过环境变量或 Makefile 变量覆盖。
---

**编译结束**: 2026-06-10 11:10
**最终状态**: built
