# Data-Peek 0.53 适配笔记

## 编译环境
- 构建系统: Perl XS (ExtUtils::MakeMaker)
- 编译日期: 2026-06-10
- 编译器: clang 18.1.8
- 状态: built

## 编译步骤

1. **初始化编译环境**
   - 从 CPAN 下载源码包 Data-Peek-0.53.tar.gz
   - 解压到 ~/tmp/builds/Data-Peek-0.53.work
   - 运行 ohc-run.py init-build 创建归档骨架

2. **修改 Makefile.PL 添加链接参数**
   参考 perl-dbd-pg 的成功经验，在 Makefile.PL 的 %wm 哈希中添加：
   ```perl
   dynamic_lib  => { OTHERLDFLAGS => '-nostartfiles --sysroot=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot -L/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos -l:libunwind.a -lc' },
   ```
   这解决了鸿蒙系统缺少 CRT 文件（crti.o, crtn.o, crtbeginS.o, crtendS.o）的问题。

3. **生成 Makefile**
   ```bash
   export PERL_MM_USE_DEFAULT=1
   cd ~/tmp/builds/Data-Peek-0.53.work
   perl Makefile.PL PREFIX=/storage/Users/currentUser/usr/local \
     INC="-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include \
         -I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/aarch64-linux-ohos"
   ```

4. **编译**
   ```bash
   make -j1
   ```
   成功生成 blib/arch/auto/Data/Peek/Peek.so

5. **Staging 安装**
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```

6. **生成补丁**
   ```bash
   ohc-run.py refresh-patch --auto Data-Peek 0.53
   ```
   生成 0001-Makefile.PL.patch

7. **打包预编译包**
   ```bash
   ohc-run.py package Data-Peek 0.53
   ```
   生成 Data-Peek-0.53-ohos-aarch64.tar.gz (110KB)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接错误：缺少 crti.o, crtn.o, crtbeginS.o, crtendS.o | 鸿蒙系统缺少 CRT 文件 | 添加 `-nostartfiles` 参数跳过 CRT |
| 2 | 链接错误：unable to find library -lc | `-nodefaultlibs -lc` 禁用了库搜索路径 | 添加 `--sysroot` 和 `-L` 指定 sysroot 和 llvm 库路径 |
| 3 | 链接错误：unable to find library -l:libunwind.a | 缺少 libunwind 库路径 | 添加 `-L/data/service/hnp/.../llvm/lib/aarch64-linux-ohos -l:libunwind.a` |
| 4 | SELinux 限制：用户目录 .so 无法加载 | 鸿蒙 SELinux 策略限制 | 无法解决，需要系统管理员权限 |

## 核心修改

**Makefile.PL 修改**（固化到补丁）：
```diff
+    ## OpenHarmony: Missing CRT files (crti.o, crtn.o, crtbeginS.o, crtendS.o)
+    ## Use -nostartfiles to skip CRT, add sysroot and lib paths
+    dynamic_lib  => { OTHERLDFLAGS => '-nostartfiles --sysroot=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot -L/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos -l:libunwind.a -lc' },
```

## 依赖版本

- Perl: 5.42.0 (系统预装)
- OHOS SDK: 26.0.0.18
- Clang: 18.1.8
- musl C 库头文件: 来自 OHOS SDK sysroot

## 编译产物

- **Peek.so**: 21KB，ELF 64-bit ARM64 共享对象
- **Peek.pm**: Perl 模块文件
- **DP.pm**: 快捷别名模块

## 验证结果

```bash
# 编译验证
cd ~/tmp/builds/Data-Peek-0.53.work
make -j1
# ✅ 成功生成 Peek.so

# 质量门禁
ohc-run.py verify-build Data-Peek 0.53
# ✅ G1-G4 全部通过

# 打包验证
ohc-run.py package Data-Peek 0.53
# ✅ Data-Peek-0.53-ohos-aarch64.tar.gz 已生成
```

## 交付物

- **预编译包**: Data-Peek-0.53-ohos-aarch64.tar.gz (110KB)
- **补丁文件**: 0001-Makefile.PL.patch
- **归档目录**: archives/d/Data-Peek/0.53/

## 知识沉淀

**新增知识（已写入 manifest）**：
1. Perl XS 模块编译需要标准 C 库头文件（OHOS SDK sysroot）
2. 鸿蒙系统缺少 CRT 文件，链接需要 -nostartfiles 参数
3. 链接 Perl XS 模块需要添加 sysroot 和 llvm 库路径，并链接 libunwind.a 和 libc
4. Makefile.PL 中可通过 dynamic_lib => { OTHERLDFLAGS => ... } 添加链接参数

**平台限制（无法解决）**：
- 鸿蒙 SELinux 策略限制用户目录 .so 文件加载
- 需要系统管理员权限将模块安装到系统 Perl 目录

## 与 perl-dbd-pg 的对比

| 项目 | Data-Peek | perl-dbd-pg |
|------|-----------|-------------|
| 构建系统 | Perl XS | Perl XS |
| 链接参数 | `-nostartfiles --sysroot=... -L... -l:libunwind.a -lc` | `-nostartfiles -nodefaultlibs -lc` |
| 需要库路径 | ✅ 需要 sysroot 和 llvm 路径 | 可能已通过其他方式解决 |
| 编译状态 | built | built |

---

**编译结束**: 2026-06-10 15:59
**最终状态**: built (编译成功，补丁固化，打包完成)
---

**编译结束**: 2026-06-10 16:00
**最终状态**: built
