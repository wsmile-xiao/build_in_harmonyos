# ZArith 1.14 适配笔记

## 编译环境
- 构建系统: 自定义 configure 脚本 (非标准 autotools)
- 编译日期: 2026-07-02
- 编译器: clang
- 状态: success

## 编译步骤
1. 下载源码: release-1.14.tar.gz
2. 配置: ./configure -installdir <prefix>/lib/ocaml
   - CFLAGS=-I/storage/Users/currentUser/usr/local/include
   - LDFLAGS=-L/storage/Users/currentUser/usr/local/lib
3. 编译: make -j1
4. 安装: make install

## 遇到的问题与解决方案
- GMP 依赖: GMP 不在 Conan channel 中，使用系统安装的 GMP
- configure 参数: ZArith 使用 -installdir 而非 --prefix
- 单线程编译: 使用 -j1 避免竞态条件

## 依赖版本
- OCaml 4.14.1 (系统安装)
- GMP 6.3.0 (系统安装于 /storage/Users/currentUser/usr/local)

## 验证结果
- zarith.cma / zarith.cmxa 库文件正常生成
- ocamlfind list | grep zarith 可找到 zarith 包
- 测试套件: make tests (上游自测)

## 注意事项
- ZArith 是 Rocq 的依赖项 (大整数运算)
- GMP 必须先于 ZArith 安装
