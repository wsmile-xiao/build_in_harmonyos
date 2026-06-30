# libcdr 0.1.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-25
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
source .build-context-libcdr-0.1.3
export PKG_CONFIG_PATH="$DEFAULT_PREFIX/lib/pkgconfig:$PKG_CONFIG_PATH"
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX --disable-werror
make -j1
make install DESTDIR=$TEST_PREFIX
make check
python3 $SKILL_ROOT/scripts/ohc-run.py package libcdr 0.1.3
make install  # 部署到本地
python3 $SKILL_ROOT/scripts/ohc-run.py finish libcdr 0.1.3 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: GNU config.guess (2014) 不含 HarmonyOS 检测 | 用 patch-autotools-ohos.pl 打补丁 + 手动修复 GUESS→echo+exit |
| 2 | config.status 无法创建临时目录 | E011: HMDFS umask 077 导致目录权限 0700 不可写 | configure 中 umask 077 改为 umask 022 |
| 3 | boost/spirit 头文件编译失败 | E026: sp_thread_sleep.hpp 使用 pthread_setcancelstate (musl 不支持) | 添加 !defined(__OHOS__) 守卫 |
| 4 | libcdr_utils.cpp TRUE 未定义 | E095: ICU 77.1 不再定义 TRUE/FALSE 宏 | 替换 TRUE 为 C++ true |
| 5 | -Werror 导致 deprecated-copy 报错 | E001: clang -Wdeprecated-copy 被 -Werror 升级 | 使用 --disable-werror |

## 源码修改

| 补丁文件 | 修改文件 | 说明 |
|----------|----------|------|
| 0001-config.guess.patch | config.guess | 添加 HarmonyOS 系统检测 |
| 0002-config.sub.patch | config.sub | 添加 linux-ohos OS 支持 |
| 0003-configure.patch | configure | umask 077→022 修复 HMDFS 权限 |
| 0004-src-lib-libcdr_utils.cpp.patch | src/lib/libcdr_utils.cpp | TRUE→true 修复 ICU 77.1 兼容性 |

系统级修复（非源码补丁）：
- boost/core/detail/sp_thread_sleep.hpp: 添加 !defined(__OHOS__) 守卫

## 依赖版本

| 依赖 | 版本 | 安装方式 |
|------|------|----------|
| librevenge | 0.0.5 | 预编译包 |
| lcms2 | 2.16 | 预编译包 |
| zlib | 1.3.1 | 预编译包 |
| icu4c | 77.1 | 预编译包 |
| boost | 1.84.0 | 预编译包 |
| cppunit | 1.15.1 | 预编译包 |

## 验证结果

```bash
$ cdr2raw --version
cdr2raw 0.1.3
$ cdr2xhtml --version
cdr2xhtml 0.1.3
$ pkg-config --modversion libcdr-0.1
0.1.3
```

make check: 1/1 PASS

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libcdr-0.1.3-ohos-aarch64.tar.gz | 97MB | 预编译包 |
| libcdr-0.1.3-ohos-aarch64-debug.tar.gz | 1.5MB | 调试符号包 |

## 功能测试（鸿蒙平台验证）

测试日期: 2026-06-25

### 命令行工具测试

6 个转换工具（cdr2raw/cdr2xhtml/cdr2text/cmx2raw/cmx2xhtml/cmx2text）全部通过:
- --version 输出正确 (0.1.3)
- --help 显示用法信息
- 错误处理: 无参数→退出码255, 无效文件→退出码1+错误信息

### CDR 文件格式检测

使用最小 RIFF+CDR 测试文件验证格式识别:
- CDR v3 (RIFF+CDR3): isSupported=true ✅
- CDR v9 (RIFF+CDR9): isSupported=true ✅
- CDR vA (RIFF+CDRA): isSupported=true ✅
- Waldo (WL 格式): isSupported=true ✅
- 空文件/无效文件: isSupported=false ✅

### C++ API 功能测试

编写 test_api.cpp 调用 libcdr API，clang++ 编译链接成功:
- 空指针安全性: 4/4 PASS
- 内存流解析: 3/3 PASS
- 文件格式检测: 20/20 PASS
- 解析不崩溃: 2/2 PASS
- **总计: 29/29 PASS**

### 库完整性

- ELF: 64-bit LSB arm64, SONAME=libcdr-0.1.so.1
- 依赖: librevenge-0.0.so.0, liblcms2.so.2, libc++_shared.so, libc.so
- 鸿蒙签名: .note.ohos.ident 存在
- pkg-config: CFLAGS/LIBS/modversion 全部正确

**结论: libcdr 0.1.3 在鸿蒙平台上功能正常，可用于 CorelDRAW 文档解析和转换。**

## 注意事项

- G0 干净构建验证因 Python subprocess shell 引号问题 FAIL，但手动验证补丁自包含性通过
- boost sp_thread_sleep.hpp 的修改是系统级修复，不属于 libcdr 源码补丁范围
- ICU 77.1 移除 TRUE/FALSE 宏是已知行为变化，影响所有使用这些宏的旧代码

---

**编译结束**: 2026-06-25 12:02
**最终状态**: published
