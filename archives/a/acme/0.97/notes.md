# acme 0.97 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile, 无 configure 脚本)
- 编译日期: 2026-06-10
- 编译器: clang 15.0.4
- 目标架构: aarch64 (OpenHarmony / HarmonyOS)
- 状态: built

## 编译步骤

1. **源码获取**: Savannah 官方下载不可达 (无 tar.gz 释放包, SVN 不可用), 使用 GitHub 镜像 sunsided/acme-crossass v0.97 tag, 通过 GitHub API (api.github.com) 下载 tarball (468KB)
2. **源码修正**: init-build 的嵌套源码检测错误地将 `contrib/toacme/src` 提升到顶层, 手动修复为使用 `src/` 目录下的真正 acme 汇编器源码。在 manifest.yaml 设置 `build_subdir: src` 指定正确子目录。
3. **Makefile 修改** (详见补丁 0001-Makefile-openharmony-adaptations.patch):
   - CC: gcc → clang
   - CFLAGS: -O3 → -fPIC -O2 (适配 OpenHarmony RPATH 和 ELF 签名要求)
   - PREFIX: 新增变量, 默认 /usr/local
   - BINDIR: /usr/local/bin → $(PREFIX)/bin
   - strip: 链接步骤中移除 `strip acme` 命令 (交由打包管线处理)
   - DESTDIR: install 目标增加 DESTDIR 支持
4. **编译**: `make PREFIX=$DEFAULT_PREFIX`
5. **安装(staging)**: `make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`
6. **安装(local)**: `make install PREFIX=$DEFAULT_PREFIX`
7. **验证**: `acme --version` → "This is ACME, release 0.97"

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah 官方源码 URL 404/超时 | Savannah nongnu 的 acme 项目没有发布 tar.gz 释放包, SVN 仓库在当前环境不可用 | 使用 GitHub 镜像 sunsided/acme-crossass v0.97 tag, 通过 GitHub API (api.github.com) 下载 tarball |
| 2 | GitHub HTTPS 直接下载超时 | 网络环境限制 HTTPS 出站到 github.com 域名 | 使用 GitHub API 域名 (api.github.com) 可正常访问, 用 Python urllib 下载 |
| 3 | 嵌套源码检测错误 | init-build 的 `_promote_nested_source` 算法按字母顺序搜索最浅层包含 Makefile 的子目录, `contrib/toacme/src` 被优先于 `src/` 提升 | 在 manifest.yaml 设置 `build_subdir: src`, 手动重建 .orig/.work 目录 |
| 4 | Makefile 无 DESTDIR 支持 | 原始 Makefile 的 install 目标不支持 DESTDIR 变量 | 修改 install 目标: `install -d $(DESTDIR)$(BINDIR)` |
| 5 | Makefile 内嵌 strip | 链接步骤包含 `strip acme`, 与打包管线的 strip/签名步骤冲突 | 移除 Makefile 中 strip 命令, 交由 ohc-run.py package 处理 |
| 6 | G0 补丁路径不匹配 | 补丁中包含绝对路径或 `src/Makefile` 相对路径, 与 clean-verify 的 build_subdir 机制冲突 | 重写补丁使用相对于 src/ 目录的路径 (`a/Makefile` → `b/Makefile`), 配合 build_subdir=src |
| 7 | manifest.yaml 编码损坏 | 知识整理写入中文字符时编码错误 (UTF-8 解码失败于字节 0xbf) | 重写 manifest.yaml 为纯 ASCII 英文内容 |
| 8 | G0 make install DESTDIR 冲突 | manifest configure_options 中硬编码 DESTDIR=$TEST_PREFIX, 与 G0 的 DESTDIR 参数冲突 | 从 configure_options 中移除 DESTDIR 和 PREFIX, 让构建管线自动处理 |

## 源码修改

- **0001-Makefile-openharmony-adaptations.patch**: 修改 CC/CFLAGS/PREFIX/BINDIR/DESTDIR/strip (6处修改)
  - CC: gcc → clang
  - CFLAGS: -O3 → -fPIC -O2
  - PREFIX: 新增 `PREFIX ?= /usr/local`
  - BINDIR: /usr/local/bin → $(PREFIX)/bin
  - 移除链接步骤中的 `strip acme`
  - install 目标增加 DESTDIR 支持

## 依赖版本

- 无外部依赖 (acme 是独立的 6502/65C02/65816 交叉汇编器)
- libm (-lm): 系统 musl libc 提供, 无需额外安装

## 真实执行验证结果

### 功能测试 (11项全部通过)

| 测试 | 内容 | 结果 |
|------|------|------|
| T1 | 版本号: `acme --version` → "release 0.97 ("Zem")" | ✅ PASS |
| T2 | 纯 6502: lda#$42/sta$d020/rts → 机器码 a942 8d20d0 60 (6字节) | ✅ PASS |
| T3 | 多指令循环: 23字节, INX/CPX/BNE 循环完整 | ✅ PASS |
| T4 | 数据段+符号: 27字节, !byte 数据和符号引用正确 | ✅ PASS |
| T5 | 字符串编码: 47字节, !text "Hello from ACME on OpenHarmony!" ASCII 正确 | ✅ PASS |
| T6 | 子程序调用: JSR clear_screen/RTS 结构正确 | ✅ PASS |
| T7 | CBM PRG 格式: 8字节, PRG 头部 (0801) 正确 | ✅ PASS |
| T8 | !source 库引用: 6502/std.a 加载正常 | ✅ PASS |
| T9 | 错误检测: 未定义标签正确报错, 拒绝生成输出 | ✅ PASS |
| T10 | 重复汇编: 输出文件正确覆盖, 6字节一致 | ✅ PASS |
| T11 | 无参数帮助: 输出版权和帮助信息 | ✅ PASS |

### 编译警告 (3个, 不影响功能)

```
mnemo.c:1151: warning: cast to smaller integer type 'int' from 'void *'
mnemo.c:1152: warning: cast to smaller integer type 'int' from 'void *'
output.c:249: warning: cast to smaller integer type 'enum output_format' from 'void *'
```

这些警告属于上游代码风格问题 (在32位平台正常, 64位平台指针8字节→int 4字节), 不影响功能正确性。

### ELF 文件属性

```
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| acme-0.97-ohos-aarch64.tar.gz | 165KB | 预编译包 (含 ELF 签名, strip 后) |
| acme-0.97-ohos-aarch64-debug.tar.gz | 47KB | 调试符号包 |

## 注意事项

- acme 无内置测试套件 (Makefile 中无 check 目标), 通过手动汇编验证功能
- acme 的标准库 (ACME_Lib/) 未包含在预编译包中, 用户需设置 `ACME` 环境变量指向库路径, 或从源码包获取
- acme 的 !source 指令依赖 `ACME` 环境变量定位库文件, 在某些受限环境中可能需要使用绝对路径或复制库文件到本地目录
- 编译警告 (void* → int cast) 属于上游代码风格, 不会导致运行时错误

## 知识条目

- ✅ E105: acme 纯 Makefile 需手动适配 OpenHarmony (CC/CFLAGS/PREFIX/BINDIR/DESTDIR/strip)
- ✅ E106: build_subdir 提示防止错误嵌套源码提升 (contrib/ vs src/)
- ✅ E107: acme 无测试套件, 通过手动汇编验证功能
- ✅ E108: acme 依赖 libm (-lm), 由系统 musl libc 提供

---
**编译结束**: 2026-06-10
**最终状态**: built
**G0-G4 门禁**: 全部 PASS