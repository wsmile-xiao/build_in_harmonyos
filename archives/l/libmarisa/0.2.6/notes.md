# libmarisa 0.2.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang/clang++ (LLVM 15.0.4)
- 状态: built

## 编译步骤

1. 下载源码: https://github.com/s-yata/marisa-trie/archive/refs/tags/v0.2.6.tar.gz
2. 解压源码，发现是完整的 marisa-trie 项目（包含 lib/ 和 bindings/）
3. 运行 autoreconf -i 生成 configure 脚本
4. 修复 HMDFS umask 问题: sed -i 's/umask 077/umask 022/g' configure
5. 运行 ./configure --prefix=$DEFAULT_PREFIX
6. 运行 make -j$(nproc)
7. 运行 make install DESTDIR=$TEST_PREFIX
8. 运行 make check (5 tests PASS)
9. 运行 make install 安装到本地
10. 制作预编译包 (ohc-run.py package)
11. 调用 ohc-run.py finish

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 嵌套源码检测错误 | bindings 目录被误判为嵌套源码 | 手动重新解压 tarball，使用正确根目录 marisa-trie-0.2.6 |
| 2 | configure 脚本不存在 | 项目只有 configure.ac，需要 autoreconf | 运行 autoreconf -i 生成 configure |
| 3 | HMDFS 文件系统 hmmac 限制 | umask 077 导致临时文件无法创建 | sed -i 's/umask 077/umask 022/g' configure |

## 源码修改

无源码修改（仅 configure 中的 umask 修复，属于运行时修补，不是源码补丁）

## 依赖版本

- autoreconf: autoconf 2.72, automake 1.17, libtool 2.4.7
- clang: 15.0.4
- make: GNU Make 4.4.1

## 验证结果

```bash
# 测试套件
make check: 5 tests PASS (base-test, io-test, vector-test, trie-test, marisa-test)

# 功能验证
marisa-build --help: 正常显示帮助信息
marisa-lookup --help: 正常显示帮助信息

# 库文件
libmarisa.so.0.0.0: 850KB
libmarisa.a: 1.3MB
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmarisa-0.2.6-ohos-aarch64.tar.gz | 2.7MB | 预编译包（含库和工具） |
| libmarisa-0.2.6-ohos-aarch64-debug.tar.gz | 3.3MB | 调试符号包 |

## 注意事项

1. 此项目需要 autoreconf -i 生成 configure 脚本，不是标准 autotools 发布包
2. HMDFS 文件系统需要修改 configure 中的 umask 设置（077 → 022）
3. 补丁主要是 autoreconf 生成的文件，源码本身无修改
---

**编译结束**: 2026-06-02 10:11
**最终状态**: built
