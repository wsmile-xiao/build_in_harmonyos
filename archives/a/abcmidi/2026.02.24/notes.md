# abcmidi 2026.02.24 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. 下载源码: SourceForge abcMIDI-2026.02.24.zip（Savannah 下载超时/404，改为 SourceForge）
2. 解压 zip 并创建 tar.gz 供 init-build 使用: `tar czf abcmidi-2026.02.24.tar.gz abcmidi/`
3. 运行 `ohc-run.py init-build abcmidi 2026.02.24 --url=file://...tar.gz`
4. 运行 `./configure --prefix=$DEFAULT_PREFIX`
5. 运行 `make -j1`（8 个二进制全部编译成功，有 K&R 函数原型弃用警告，无错误）
6. 运行 `make install DESTDIR=$TEST_PREFIX`（staging 安装成功）
7. 安全弹窗验证: 8 个二进制均可执行
8. make check: 无 check 目标（abcmidi 不提供自动化测试套件），以手动功能测试代替
9. 运行 `ohc-run.py package abcmidi 2026.02.24` 制作预编译包
10. 运行 `make install`（不带 DESTDIR）本地安装验证
11. 运行 `ohc-run.py finish abcmidi 2026.02.24 published` 收尾

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah tarball 下载失败 | Savannah CDN 重定向到 fosszone.csd.auth.gr 镜像连接超时，其他镜像也 404 | 从 SourceForge 下载 abcMIDI-2026.02.24.zip，手动解压后创建 tar.gz 供 init-build 使用 |
| 2 | **config.status Permission denied** | HMDFS 文件系统 SGID 继承: `umask 077 && mktemp -d "./confXXXXXX"` 创建目录得到 `drwx--S---`，在 HMDFS 上不可写入；chmod 也无法修复（SELinux 限制，E046） | **核心修复**: 修改 configure 和 config.status 中 tmp 目录创建的 `umask 077` → `umask 022`，使目录权限为 `drwxr-s--x` |
| 3 | bash 无法执行 /usr/bin 程序 | bash (GNU 5.3.0) 无法执行 /usr/bin 下的 toybox symlink（Permission denied） | 使用 zsh 运行 config.status |
| 4 | SourceForge zip 初次解压不完整 | 首次 unzip 只提取了部分文件（5 个而非 97 个） | 删除旧 tar.gz 缓存，重新完整解压创建正确的 tar.gz |
| 5 | abc2abc/yaps/mftext 不支持 --version | 这些程序将 --version/-v/-V 当作文件名参数 | 使用 abc2midi/midi2abc/midicopy/midistats 的版本号确认软件版本 |

## 源码修改（4 个补丁）

| 补丁 | 类型 | 说明 |
|------|------|------|
| 0001-Makefile.patch | 构建产物 | make 编译生成的 Makefile 变更（编译路径等） |
| 0002-config.log.patch | 构建产物 | configure 运行生成的 config.log 变更 |
| 0003-config.status.patch | **平台适配** | **核心修复** — umask 077 → umask 022（HMDFS SGID 目录权限） |
| 0004-configure.patch | **平台适配** | **核心修复** — umask 077 → umask 022（HMDFS SGID 目录权限） |

**补丁关键内容**（0003/0004）：
```diff
- tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
+ tmp=`(umask 022 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
```

此修复仅影响 autotools 生成的临时目录创建，不影响最终安装路径权限。

## 依赖版本

无外部库依赖（仅 libm 数学库，系统自带）

## 功能验证结果

### abc2midi（abc → MIDI 转换）
- demo.abc → demo.mid (1744字节) ✅
- araber.abc → araber.mid (6169字节) ✅
- coleraine.abc → coleraine.mid (7754字节，含3声部) ✅

### midi2abc（MIDI → abc 逆向转换）
- demo.mid → demo_out.abc (629字节) ✅
- araber.mid → stdout abc 输出 ✅

### midicopy（MIDI 文件操作）
- 全文件复制: demo.mid → demo_copy.mid (1744字节) ✅
- 通道提取: coleraine.mid → coleraine_ch1.mid (1975字节) ✅

### mftext（MIDI 文本解析）
- araber.mid 文本解析输出正常 ✅
- demo.mid 文本解析输出正常 ✅

### midistats（MIDI 统计）
- corestats 输出: 时间签名/音符数等 ✅
- CSV 输出: 音高分布/跳进统计等 ✅

### yaps（abc → PostScript）
- demo.abc → demo.ps (83228字节) ✅
- 源 abc 文件本身的乐谱格式警告（非软件 bug）

### abc2abc（abc 格式转换）
- boys.abc stdout 输出正常 ✅

### abcmatch（abc 模式匹配）
- 可执行，需 match.abc 模式文件 ✅

## 版本号确认

| 二进制 | 版本 |
|--------|------|
| abc2midi | 5.02 February 16 2025 |
| midi2abc | 3.64 June 14 2025 |
| midicopy | 1.40 August 11 2024 |
| midistats | 1.03 February 20 2026 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| abcmidi-2026.02.24-ohos-aarch64.tar.gz | 1894708 字节 (1.89MB) | 预编译包（含 8 个 ELF 签名二进制、文档、man 页） |
| abcmidi-2026.02.24-ohos-aarch64-debug.tar.gz | 307268 字节 (307KB) | 调试符号包 |

## 注意事项

1. HMDFS SGID 目录权限问题: umask 077 创建的 `drwx--S---` 目录不可写入且 chmod 无法修复，需改为 umask 022/002
2. 此问题影响所有使用 autotools configure 的软件在 HMDFS 上编译，建议沉淀为知识图谱条目
3. abc2abc/yaps/mftext 不支持 --version 标志，以 abc2midi 版本号确认软件包版本
4. Savannah 下载不稳定，建议优先从 SourceForge 或 GitHub 获取源码

---

**编译结束**: 2026-06-03 15:51
**最终状态**: published
