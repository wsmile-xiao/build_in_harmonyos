# libvisio 0.1.11 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-22
- 编译器: clang/clang++ (OHOS SDK 26.0.0.18)
- 状态: built

## 编译步骤

1. `autogen.sh` (需设置 AUTOM4TE 环境变量)
2. `./configure --prefix=$DEFAULT_PREFIX --disable-tests --disable-tools --enable-static --disable-shared`
3. `make -j2`
4. `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aclocal 失败 | @am_AUTOM4TE@ 未替换 | 设置 AUTOM4TE 环境变量 |
| 2 | configure shebang | E165: /bin/sh 不存在 | sed 替换为 /system/bin/sh |
| 3 | config.status mktemp 失败 | E002: HMDFS 不支持 mktemp | 创建 mktemp wrapper 脚本 |
| 4 | configure "cannot run C compiled programs" | LIBS 环境变量干扰基础编译器测试 | 不设置 LIBS，使用 rpath |
| 5 | LD_LIBRARY_PATH 导致 lld 崩溃 | lld 自身链接 libxml2，LD_LIBRARY_PATH 导致版本冲突 | 使用 -Wl,-rpath 替代 LD_LIBRARY_PATH |
| 6 | .la 文件 libdir 为 //lib | conan 包安装时 libdir 未正确设置 | 修复 .la 文件中的 libdir 路径 |
| 7 | ICU 静态库 -fPIC 链接失败 | ICU 静态库未编译 -fPIC | 使用 --enable-static --disable-shared |
| 8 | config.guess 不识别 HarmonyOS | E007: 无 OHOS 检测分支 | perl patch-autotools-ohos.pl |
| 9 | PkgConfigDeps .pc 文件名不匹配 | librevenge.pc vs librevenge-0.0.pc | 创建 .pc 文件别名 |
| 10 | test_package librevenge 头文件未找到 | librevenge 包未暴露 includedirs | CMakeLists.txt 手动添加 include 路径 |

## 源码修改

无补丁文件。所有修改在 conanfile.py 的 build() 方法中运行时完成。

## 依赖版本

- boost/1.90.0@ohpcd/stable (header-only)
- librevenge/0.0.5@ohpcd/stable (static)
- icu4c/78@ohpcd/stable (static)
- libxml2/2.15.3 (static)
- zlib/1.3.1 (static)

## 验证结果

```bash
conan create archives/l/libvisio/0.1.11 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# G0-G4, L2/L4/L5 全部通过
```

## 注意事项

- AUTOM4TE 环境变量必须在 build() 中设置
- .la 文件 libdir 修复是 conan 包安装问题，非源码问题
- 静态构建是唯一选项（ICU 静态库未编译 -fPIC）
---

**编译结束**: 2026-07-22 18:43
**最终状态**: built
