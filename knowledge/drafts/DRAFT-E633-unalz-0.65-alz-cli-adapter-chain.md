# DRAFT-E633：unalz 0.65（ALZ/AlZip 解压 CLI）适配链——Makefile 硬编码编译器、musl iconv 韩文文件名、EUC-KR 源码树的补丁生成边界

> Contributor: unalz-0.65 任务 | Status: Draft | Updated: 2026-09-21
> Source: feat/unalz-0.65（新包首适配，官方站 kipple.pe.kr 不可达，源取 deb.debian.org pristine orig）

## 背景

unalz 0.65 是 2009 年的纯 Makefile C++ 项目（ALZ/AlZip 归档解压 CLI），源码
main.cpp/UnAlz.cpp 为 **EUC-KR + CRLF** 编码，捆绑 zlib 1.2.3 与 bzip2 解压子集，
无 configure、无测试套件。在 HarmonyOS PC（musl + clang 15 + cppstd=17）适配时
暴露五类问题；逐项修复后 `conan create` 干净轮 + test_package 28/28 全过。

## 问题 1：Makefile 硬编码 `CC = gcc` / `CPP = g++`

### 现象

conan 环境（profile `tools.build:compiler_executables` 指向 `/data/service/hnp/bin/clang`）
不生效，构建找 g++。

### 根因与修复

上游 Makefile 顶部硬编码（且把 C++ 编译器命名为 `CPP`）。make **命令行变量**优先级
高于文件内赋值，配方里显式传：

```python
comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
cc = comp_execs.get("c") or "clang"
cxx = comp_execs.get("cpp") or "clang++"
self.run(f'make -j1 linux-utf8 CC="{cc}" CXX="{cxx}" CPP="{cxx}"', cwd=self.source_folder)
```

不读裸 shell 环境变量（R33）。

## 问题 2：`-liconv` 链接失败与 CP949 文件名转换

上游 `posix`/`posix-utf8` 目标链接 `-liconv`——musl 无独立 libiconv，直接失败。
OHOS 的 musl libc **内置 iconv 且支持 CP949/EUC-KR 别名**（10 行探针实测：
`iconv_open("UTF-8","CP949")` ok，`\xc5\xd7\xbd\xba\xc6\xae.txt` 正确转成 테스트.txt）。
因此选 `linux-utf8` 目标（`-D_UNALZ_ICONV -D_UNALZ_UTF8`，不带 `-liconv`），
韩文文件名→UTF-8 转换实测可用（test_package T8）。

## 问题 3：C++17 下 `register` 从告警升级为硬错误

### 现象

设备裸 `make`（无 `-std`，clang 默认 gnu++14）只有 `-Wdeprecated-register` 告警、
构建通过；conan 里 G2 却报：

```text
UnAlz.cpp:1938:2: error: ISO C++17 does not allow 'register' storage class specifier
```

### 根因

profile `compiler.cppstd=17` 经 GnuToolchain 进 CXXFLAGS（`-std=c++17`），make 的
**内建隐式规则**（`%.o: %.cpp`）吃到该标志，`register` 在 C++17 是硬错误。
"设备全绿不构成 CI 会绿的证据"的又一实例。

### 修复

去掉两处 `register ` 存储类说明符（零语义影响，C++98/14/17 全兼容）。

## 问题 4：EUC-KR+CRLF 源码树的补丁生成与校验链

### 现象

refresh-patch 生成的补丁全部 `dry-run 失败`，`patches/` 落空、conandata 引用悬空。

### 根因（四层叠加）

1. `read_text()` 的 universal-newlines 在**读取时**把 CRLF 折成 LF——补丁上下文
   与 CRLF 目标文件字节失配；
2. `read_text(encoding="utf-8", errors="replace")` 把 EUC-KR 字节替换成 U+FFFD；
3. 设备 `/usr/bin/patch` 是 toybox：对补丁上下文剥 DOS newlines 后匹配 CRLF
   文件必败（最小夹具实测）；
4. OHOS python subprocess 对裸命令名 `"patch"` 不做 PATH 搜索（恒 ENOENT），
   旧 dry-run 实现异常吞掉后恒 False。

### 修复（容器层 overlay，非本 PR 内容）

`_diff_files` 改 read_bytes + latin-1 1:1 映射（补丁与原文件逐字节一致，写盘
write_bytes）；dry-run 优先 `git apply --check -p1`（字节匹配、CRLF 安全）。
conan 侧实际应用补丁走 patch_ng（纯 python 字节级，CRLF/EUC-KR 三形态实测均可）。

## 问题 5：CLI 无 --version/--help、错误路径恒 return 0

上游仅在无参调用时打印 `unalz v0.65 (2009/04/01)` 横幅；`--version` 会被当作
归档文件名。补丁 0002-main.cpp 增加 `-v/--version`（打印横幅退出 0）与
`-h/--help`（打印 Usage 退出 0）。另：上游错误路径（文件缺失/损坏）一律
`return 0`——test_package 断言打输出文本（"file open error"/"It's corrupted
file."），并把 rc==0 显式断言为上游行为。

## 最小 ALZ 夹具（运行时生成，不提交二进制归档）

```python
b"ALZ\x01" + le32(0)                    # 全局头
b"BLZ\x01" + le16(namelen) + b"\x20"    # 本地头：文件名长 + attr=FILE
  + le32(dos_time) + b"\x40" + b"\x00"  #   fileDescriptor 0x40 = 4 字节长度字段
  + b"\x00" + b"\x00" + le32(crc32)     #   压缩方法 0=stored + CRC32（解压强校验）
  + le32(csize) + le32(usize) + name + content
b"CLZ\x01" + le32(0) + le32(0) + b"CLZ\x03"   # 中央目录（12 字节头）
b"CLZ\x02"                                     # 结尾
```

文件名按 EUC-KR 编码写入（테스트.txt → `\xc5\xd7\xbd\xba\xc6\xae.txt`），
配合 `-utf8` 验证码页转换。

## 验证

- `conan create` 干净轮（apply_patch×2 / run_make×2 / calling_build×1）
- test_package：**PASS=28 FAIL=0**（9 用例）
- iconv 探针：CP949/EUC-KR/EUCKR 三别名 ok，转换输出正确

## 关联

- 触发 error_signature 见同目录 .kv（DRAFT-E633-unalz-0.65-alz-cli-adapter-chain.kv）
- manifest knowledge_gained 已按 `# knowledge_ref: E633` 行尾注释引用
