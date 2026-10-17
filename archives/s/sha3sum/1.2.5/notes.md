# sha3sum 1.2.5 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-07
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 源码下载: https://codeload.github.com/maandree/sha3sum/tar.gz/refs/tags/1.2.5
2. 安装依赖: libkeccak 1.4.3 (预编译包)
3. 应用补丁 0001-config.mk.patch: CC=c99→clang, 禁用SANITIZE (CFLAGS/LDFLAGS清除SANITIZE引用)
4. make -j1 (通过conanfile.py build()方法传递CC/CFLAGS/CPPFLAGS/LDFLAGS变量)
5. make install PREFIX={package_folder} (conanfile.py package()方法)
6. make check (全部通过)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CC=c99 不可用 | 鸿蒙平台无c99命令 | 补丁中config.mk CC改为clang |
| 2 | libkeccak.h 找不到 | 头文件安装路径不在默认搜索路径 | conanfile.py build()通过CPPFLAGS传递-I路径 |
| 3 | -lkeccak 链接失败 | 库文件路径不在默认搜索路径 | conanfile.py build()通过LDFLAGS传递-L路径 |
| 4 | SANITIZE选项不兼容 | clang不支持部分sanitize选项 | 补丁中清除CFLAGS/LDFLAGS的$(SANITIZE)引用, build()传递CFLAGS="-fPIC -O2" |
| 5 | SSL证书验证失败 | 鸿蒙环境CA证书缺失 | 使用conan内置get()方法下载,由conan处理SSL |

## 源码修改

### config.mk 补丁修改内容 (0001-config.mk.patch):
- CC: c99 → clang
- CFLAGS: $(SANITIZE) → (空, 由conanfile.py build()覆盖)
- LDFLAGS: $(SANITIZE) -lkeccak → -lkeccak (移除SANITIZE引用)
- 注意: PREFIX/CPPFLAGS/LDFLAGS路径不在补丁中, 由conanfile.py build()通过make变量覆盖

## 依赖版本

- libkeccak 1.4.3 (预编译包安装)
- clang 15.0.4
- make 4.4.1

## 验证结果

make check 全部通过，包括:
- 空输入哈希测试 (sha3-224/256/384/512, keccak-224/256/384/512)
- shake/rawshake 测试
- 大小写输出测试 (-u/-l/-b)
- 多文件校验测试 (-c)
- NUL分隔符测试 (-z)
- 自定义参数测试 (-R/-C/-N/-S/-W/-Z)
- 十六进制输入测试 (-x)

## 交付物

| 文件 | 类型 | 说明 |
|------|------|------|
| 16个bin | bin | keccaksum, sha3sum, keccak-224/256/384/512sum, sha3-224/256/384/512sum, rawshake128/256/512sum, shake128/256/512sum |
| 16个man1 | man | 对应的man页面 |
| LICENSE | license | 许可证文件 |

## 注意事项

- libkeccak头文件中的 __optimize__("-O0") 属性在clang下会产生警告，但不影响功能
- sha3sum 是纯命令行工具，无库文件输出
- 依赖 libkeccak 的动态库 (libkeccak.so)
- 补丁不含绝对路径，路径由conanfile.py build()通过make变量动态传递
---

**编译结束**: 2026-07-07 14:34
**最终状态**: built
