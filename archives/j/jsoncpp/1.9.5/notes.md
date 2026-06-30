# jsoncpp 1.9.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-21
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

1. CMake 配置: `cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release`
2. 编译: `make -j2` - 成功，无错误
3. 测试: 内置测试在编译过程中自动运行，119 个测试全部通过
4. Staging 安装: `make install DESTDIR=$TEST_PREFIX`
5. 预编译包制作: `ohc-run.py package jsoncpp 1.9.5`
6. 本地安装验证: `make install` (不带 DESTDIR)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 历史 manifest.yaml 构建系统错误 | 旧记录为 autotools，但 jsoncpp 实际只有 cmake/meson | 更新 manifest.yaml: system: cmake |

## 源码修改

无补丁，源码无需修改即可编译通过。

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- 无外部库依赖

## 验证结果

```bash
# pkg-config 验证
$ pkg-config --modversion jsoncpp
1.9.5

# 测试程序编译执行
$ clang++ -std=c++11 test.cpp -I$DEFAULT_PREFIX/include -L$DEFAULT_PREFIX/lib -ljsoncpp
编译成功！执行成功！
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| jsoncpp-1.9.5-ohos-aarch64.tar.gz | 1350KB | 预编译包（含库+头文件） |
| jsoncpp-1.9.5-ohos-aarch64-debug.tar.gz | 340KB | 调试符号包 |

## 注意事项

- jsoncpp 无可执行文件，仅为 C++ JSON 库
- pkg-config 验证需设置 PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig
---

**编译结束**: 2026-05-21 18:00
**最终状态**: built
