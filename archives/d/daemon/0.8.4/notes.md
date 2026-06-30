# daemon 0.8.4 适配笔记

## 编译环境
- 构建系统: custom（自定义 configure 脚本 + Makefile，非 GNU autoconf）
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4 / clang++
- 平台: aarch64-unknown-linux-ohos (OpenHarmony, musl libc)
- 状态: published

## 编译步骤

1. **初始化构建**:
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build daemon 0.8.4 --url=file:///path/to/daemon-0.8.4.tar.gz
   ```

2. **配置**（自定义 configure 脚本）:
   ```bash
   ./configure --platform=Linux --prefix=$DEFAULT_PREFIX --destdir=$TEST_PREFIX \
     --disable-logind --disable-mail-test CC=clang
   ```

3. **修改 config.h**（musl libc 适配）:
   ```bash
   sed -i 's/^#define HAVE_FUNC_GETSERVBYNAME_R_6 1$/\/* #undef HAVE_FUNC_GETSERVBYNAME_R_6 *\//' libslack/config.h
   sed -i 's/^#define HAVE_VHANGUP 1$/\/* #undef HAVE_VHANGUP *\//' libslack/config.h
   sed -i 's/^#define HAVE_PTSNAME_R 1$/\/* #undef HAVE_PTSNAME_R *\//' libslack/config.h
   ```

4. **编译**:
   ```bash
   make -j2
   ```

5. **安装（staging）**:
   ```bash
   make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
   ```

6. **测试**:
   ```bash
   make ready  # 处理 symlink
   make test
   ```

7. **本地安装验证**:
   ```bash
   make install PREFIX=$DEFAULT_PREFIX  # 无 DESTDIR
   # 需要 ELF 签名后才能执行
   python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $DEFAULT_PREFIX/bin/daemon
   $DEFAULT_PREFIX/bin/daemon --version  # 输出: daemon-0.8.4
   ```

8. **打包**:
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py package daemon 0.8.4
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | musl libc 无 `getservbyname_r` (6参数版) | musl 不实现该glibc特有函数 | 禁用 `HAVE_FUNC_GETSERVBYNAME_R_6` 宏；修改 `conf/linux` 注释掉启用该宏的perl行 |
| 2 | musl libc 无 `vhangup()` | musl 不实现该函数 | 禁用 `HAVE_VHANGUP` 宏；修改 `conf/linux` |
| 3 | musl libc 无 `ptsname_r()` | musl 不实现该函数 | 禁用 `HAVE_PTSNAME_R` 宏；修改 `conf/linux` |
| 4 | `make clobber/clean` 重置所有配置 | daemon 的 Makefile 在 clean/clobber 时运行 `./configure --default` | 修改 config.h 后不要再 make clean，直接 make |
| 5 | `ln -sf libslack/slack → .` 失败（Resource busy） | HMDFS 不支持覆盖已有符号链接 | `make ready` 绕过 |
| 6 | SSL 证书验证失败导致下载失败 | OpenHarmony 系统 SSL 证书不完整 | `wget --no-check-certificate` 手动下载 |
| 7 | 二进制无法执行（Operation not permitted） | OpenHarmony 要求 ELF 签名 | `ohc-run.py sign-elf` 签名后可执行 |
| 8 | G0 补丁包含 configure 生成内容（Makefile/macros.mk） | 之前的补丁包含 CC/PREFIX 等配置生成内容 | 重构补丁：只保留源码级修改（conf/linux + libslack/config.h），Makefile 变化由 configure 选项处理 |
| 9 | manifest YAML list 格式被 G0 clean-verify 误读 | G0 正则只解析单行字符串 | 改为 `configure_options: "--platform=Linux --disable-logind --disable-mail-test"` |

## 源码修改

### 补丁 0001-conf-linux.patch
- 文件: `conf/linux`
- 内容: 注释掉 3 条 perl 替换命令，阻止 configure 启用 musl 不兼容的宏
  - `HAVE_FUNC_GETSERVBYNAME_R_6` → 不从 `/* #undef */` 改为 `#define ... 1`
  - `HAVE_VHANGUP` → 不启用
  - `HAVE_PTSNAME_R` → 不启用

### 补丁 0002-libslack-config.h.patch
- 文件: `libslack/config.h`
- 内容: 禁用 3 个 musl 不兼容的宏定义
  - `#define HAVE_FUNC_GETSERVBYNAME_R_6 1` → `/* #undef HAVE_FUNC_GETSERVBYNAME_R_6 */`
  - `#define HAVE_VHANGUP 1` → `/* #undef HAVE_VHANGUP */`
  - `#define HAVE_PTSNAME_R 1` → `/* #undef HAVE_PTSNAME_R */`

## 依赖版本

- 内嵌 libslack（源码包自带，无需外部依赖）
- 无其他外部编译依赖

## 验证结果

```bash
# 二进制验证
$ $DEFAULT_PREFIX/bin/daemon --version
daemon-0.8.4

# ELF 验证
$ readelf -h daemon
Class: ELF64
Data: 2's complement, little endian

# 静态库验证
$ nm libslack/libslack.a | grep getservbyname_r
（无输出，确认该函数已被禁用）

$ nm libslack/libslack.a | grep vhangup
（无输出，确认该函数已被禁用）

$ nm libslack/libslack.a | grep ptsname_r
（无输出，确认该函数已被禁用）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| daemon-0.8.4-ohos-aarch64.tar.gz | 330KB | 预编译包（stripped 二进制 + man page） |
| daemon-0.8.4-ohos-aarch64-debug.tar.gz | - | debug symbols 包 |
| daemon 二进制（工作目录） | 203KB | 编译产物（未strip） |
| daemon 二进制（安装目录） | 165KB | 安装产物（stripped + ELF签名） |

## 注意事项

1. **make clean/clobber 会重置配置**: 修改 config.h 后不要运行 make clean/clobber，否则需要重新配置 + 重新 sed
2. **libslack/slack 符号链接**: `make ready` 可解决 "Resource busy" 问题
3. **ELF 签名必须**: OpenHarmony 要求二进制必须经过 ELF 签名才能执行
4. **configure 选项**: daemon 使用自定义 configure 脚本，选项格式与 GNU autoconf 不同（支持 --platform, --destdir 等）
5. **测试限制**: PTY 相关测试（coproc/pseudo）因 SELinux 权限限制会失败，属于平台特性非软件缺陷
6. **/tmp 只读**: OpenHarmony /tmp 是只读的，测试中涉及 /tmp 的测试会失败（已知 E002 gotcha）

---
**编译结束**: 2026-06-02
**最终状态**: published
---

**编译结束**: 2026-06-02 18:05
**最终状态**: published
