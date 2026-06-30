# file 5.47 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **初始化编译环境**
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build file 5.47 --url=https://astron.com/pub/file/file-5.47.tar.gz
   source .build-context-file-5.47
   cd $BUILD_SRC_DIR
   ```

2. **应用 OHOS 平台补丁 (E007)**
   ```bash
   perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub
   sed -i 's/| linux-uclibc\* )/| linux-uclibc* | linux-ohos* )/' config.sub
   ```

3. **修复 HMDFS 权限问题 (E011)**
   ```bash
   sed -i 's/umask 077/umask 022/g' configure
   ```

4. **修复 LLVM linker 依赖**
   ```bash
   ln -sf /data/service/hnp/libxml2.org/libxml2_2.11.9/lib/libxml2.so.2 ~/usr/local/lib/libxml2.so.16
   ln -sf /data/service/hnp/libxml2.org/libxml2_2.11.9/lib/libiconv.so.2 ~/usr/local/lib/libiconv.so.2
   ln -sf /data/service/hnp/libxml2.org/libxml2_2.11.9/lib/liblzma.so.5 ~/usr/local/lib/liblzma.so.5
   ```

5. **配置和编译（静态模式）**
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX --disable-libseccomp --enable-static --disable-shared LDFLAGS=-static
   make -j1
   ```

6. **安装和测试**
   ```bash
   make install DESTDIR=$TEST_PREFIX
   make check  # 全部测试通过
   make install  # 本地安装
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 OHOS | GNU config.guess 不包含 HarmonyOS 检测分支 | 使用 patch-autotools-ohos.pl 补丁脚本 (E007) |
| 2 | config.sub 不支持 linux-ohos | kernel-os 组合验证列表缺少 linux-ohos* | 手动添加到 kernel-os 组合验证部分 |
| 3 | configure 临时目录权限错误 | HMDFS umask 077 导致临时目录不可写 | 修改 configure 中 umask 077 为 022 (E011) |
| 4 | LLVM linker 缺少 libxml2.so.16 | OHOS SDK lld 依赖 libxml2 但路径不在 LD_LIBRARY_PATH | 创建软链接指向 OHOS SDK 的库文件 |
| 5 | 动态库无法执行（签名问题） | 静态编译的 file 无法加载动态库 libmagic.so.1 | 使用静态编译模式 (--enable-static --disable-shared) |
| 6 | configure.ac 缺失导致 make 失败 | HMDFS 文件系统异常导致源码文件丢失 | 从 .orig 目录重新复制完整源码 |

## 源码修改

| 文件 | 修改内容 | 补丁文件 |
|------|----------|----------|
| config.guess | 添加 HarmonyOS 系统识别分支 | 0002-config.guess.patch |
| config.sub | 添加 ohos-linux 三元组支持 + kernel-os 组合验证 | 0003-config.sub.patch |
| configure | umask 077 → umask 022（修复 HMDFS 权限） | 非补丁修改，直接 sed 替换 |

## 依赖版本

- zlib: 系统自带
- bz2: 系统自带
- lzma: 系统自带
- libseccomp: 禁用（OHOS 不提供）

## 验证结果

```bash
$ $DEFAULT_PREFIX/bin/file --version
file-5.47
magic file from /storage/Users/currentUser/usr/local/share/misc/magic

$ $DEFAULT_PREFIX/bin/file $DEFAULT_PREFIX/bin/file
/storage/Users/currentUser/usr/local/bin/file: ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked, interpreter /lib/ld-musl-aarch64.so.1, with debug_info, not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| file-5.47-ohos-aarch64.tar.gz | 11.2 MB | 预编译主包 |
| file-5.47-ohos-aarch64-debug.tar.gz | 46 KB | 调试符号包 |

## 注意事项

1. **静态编译必要性**: OHOS 系统要求 ELF 文件签名，动态库签名问题复杂，静态编译更稳定
2. **umask 补丁**: 所有 autotools 项目在 HMDFS 上编译都需要修改 configure 中的 umask 077
3. **config.guess/config.sub**: 这是所有 autotools 项目编译的第一道门槛，必须先应用 OHOS 补丁
4. **libxml2/libiconv/liblzma**: OHOS SDK 的 lld 依赖这些库，需要创建软链接

---

**编译结束**: 2026-05-27 12:43
**最终状态**: built