# libscfg 0.2.0 适配笔记

## 上游信息

- **名称**: libscfg
- **版本**: 0.2.0
- **描述**: 简单的配置文件格式库（基于指令的块作用域语法）
- **上游**: https://codeberg.org/emersion/libscfg
- **许可证**: MIT
- **构建系统**: Meson (>=0.54.0)
- **语言**: C (c99)
- **依赖**: 无外部依赖

## 源码验证

| 项目 | 值 |
|------|-----|
| 主 URL | https://codeberg.org/emersion/libscfg/releases/download/v0.2.0/libscfg-0.2.0.tar.gz |
| 主 sha256 | `18bf24666aa77b12347b6dffeec32b2e7d24719698041c372ab27da80d16150c` |
| 镜像 URL | https://deb.debian.org/debian/pool/main/libs/libscfg/libscfg_0.2.0.orig.tar.gz |
| 镜像 sha256 | `11df0bf3654214ce51c2965819ce741409aa6b5403728669c5a6b8ab55c2e5d3` |
| tar 格式 | tar.gz |

sha256 来源：FreeBSD ports distfiles 校验记录（权威）。Debian 镜像是重新打包的上游 orig tarball（gzip 元数据不同，故 sha256 不同），解压后源码内容与 Codeberg tarball 完全一致（scfg.h / meson.build / parser.c / formatter.c / scfg.c / test.c 逐一比对）。

Codeberg 对 CI runner 间歇返回 HTTP 429（libjodycode 4.1.2 同实证），因此 conandata.yml 必须带 Debian mirror + mirror_sha256，source() 实现了主 URL 失败后自动切换镜像的逻辑（复用 libjodycode 4.1.2 的模式）。

## 构建系统

上游 `meson.build` 要点：
- `project('scfg', 'c', version:'0.2.0', license:'MIT', default_options:['c_std=c99','warning_level=3','werror=true'])`
- 编译源文件：`formatter.c`, `parser.c`, `scfg.c`
- 安装头文件：`include/scfg.h`
- 共享库：`libscfg.so` (version `0.2.0`, soversion `2`)
- pkg-config：生成 `scfg.pc`
- 无外部依赖，无子项目

`werror=true` 在 OHOS clang 15 下编译干净，未触发任何 warning，无需 patch。

## API

```c
struct scfg_block {
    struct scfg_directive *directives;
    size_t directives_len;
};

struct scfg_directive {
    char *name;
    char **params;
    size_t params_len;
    struct scfg_block children;
    int lineno;
};

int scfg_load_file(struct scfg_block *block, const char *path);
int scfg_store_file(const struct scfg_block *block, const char *path);
int scfg_parse_file(struct scfg_block *block, FILE *f);
int scfg_format_file(const struct scfg_block *block, FILE *f);
void scfg_block_finish(struct scfg_block *block);
```

## 编译环境

- 构建系统: meson
- 编译日期: 2026-08-24
- 编译器: clang 15 (OHOS aarch64)
- 构建配置: shared (default_library=shared)

## OHOS 适配要点

1. **ar 注入**: profile 的 `tools.build:compiler_executables` 仅设 c/cpp，未设 ar。Meson 的 native file 缺少 `ar =` 行会导致 sanity check 或静态归档失败。在 `generate()` 中向 `conan_meson_native.ini` 注入 ar，路径通过 `shutil.which("ar")` 探测（兼容本机 `/storage/.../usr/local/bin/ar` 与 CI runner `/data/service/hnp/bin/ar`）。

2. **ELF 签名**: libscfg 产物为 `libscfg.so.*`（共享库），OHOS XPM 要求 dlopen 的 .so 必须代码签名。`package()` 中调用 `_sign_binaries()`，先用 `llvm-objcopy --remove-section .codesign` 清除旧签名节，再用 `binary-sign-tool sign -selfSign 1` 写入新签名。此方法带 `os != OHOS` 守卫，非 OHOS 环境 no-op。

3. **源码镜像**: Codeberg 429 兜底，conandata.yml 带 Debian mirror + mirror_sha256。

## 源码修改

### OHOS open_memstream 兼容补丁

- **补丁文件**: `patches/ohos-open_memstream-fflush.patch`
- **补丁类型**: portability（可移植性修复）
- **根因**: OHOS aarch64 libc 的 `open_memstream` 在 `fclose` 时不会将待写数据刷新到缓冲区（违反 POSIX 规范）。libscfg 的 `scfg_format_file()` 通过 `fwrite` 写入调用方提供的 `FILE*` 后返回；上游 test.c 的 `scfg:format` 测试在 `open_memstream` → `scfg_format_file` → `fclose` → `strcmp` 序列中得到空缓冲区（str_size=0），导致测试失败。探针验证：在 `fclose` 前添加 `fflush(f)` 可使 str_size=133 且 `strcmp` 完全匹配，证明格式化输出本身字节正确。
- **修复**: 在 `formatter.c` 的 `scfg_format_file()` 末尾添加防御性 `fflush(f)` 调用。
- **API 语义**: 不改变 API 语义——在符合 POSIX 的 libc 上，对已完全写入的流调用 `fflush` 是 no-op。仅修改 `formatter.c`，不触碰 `test.c`。

## test_package

test_package 使用 CMake (CMakeDeps + CMakeToolchain) 消费 libscfg，测试程序 `test_scfg.c` 调用真实 API：
- `scfg_parse_file` + `fmemopen` 解析内存中的配置字符串
- 验证指令数量、名称、参数、子块
- `scfg_format_file` + `fmemopen` 格式化回字符串
- 重新解析格式化输出，验证 round-trip 一致性
- `scfg_block_finish` 释放内存

不依赖文件系统临时文件（使用 `fmemopen`），避免 OHOS `/tmp` 只读问题。
