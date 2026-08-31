# mp3wrap 0.5 适配笔记

## 编译环境
- 构建系统: autotools (automake 1.5, autoconf)
- 编译日期: 2026-08-31
- 编译器: clang (OHOS aarch64 cross-compiler)
- 状态: published

## 编译步骤

```bash
# 1. Conan 拉取源码并应用补丁
conan source .

# 2. 配置 (OHOS 交叉编译)
CONFIG_SHELL=/data/service/hnp/bin/bash \
./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
    --prefix=<package_folder>

# 3. 编译
make -j1

# 4. 安装
make -j1 install DESTDIR=<package_folder>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `crc.c:31: error: unknown type name 'u_int32_t'` | `u_int32_t` 是 BSD/glibc 私有类型，musl libc（OHOS）未定义 | 替换为 C99 标准 `uint32_t`（`stdint.h`），功能等价 |
| 2 | `config.status` 无法写入临时目录 | `configure` 使用 `umask 077` 创建临时目录；OHOS hmdfs 的 setgid 位使目录变为 `drwx--S---`，进程自身不可写 | 补丁将 `umask 077` 改为 `umask 022` |
| 3 | 无 `config.sub` / `config.guess` | mp3wrap 0.5 使用 automake 1.5（2003 年发布），configure 不包含这两个文件 | 直接传递 `--build` / `--host` 三元组；configure 仅探测 CC/INSTALL，不涉及目标平台检测 |

## 源码修改

### 0001-crc-uint32t.patch
- 文件: `crc.c` 第 31 行
- 修改: `static const u_int32_t crctab[256]` → `static const uint32_t crctab[256]`
- 原因: `u_int32_t` 是 BSD 遗留类型，在 glibc 中通过 `<sys/types.h>` 间接定义，但 musl libc（OHOS 使用的 C 库）不提供该类型。`uint32_t` 是 C99 标准（`<stdint.h>`）的等价类型，已包含在 `crc.c` 的 `<stdio.h>`/`<stdlib.h>` 传递依赖中。这是最小改动，不涉及任何逻辑重构。

### 0002-configure-umask-022.patch
- 文件: `configure` 第 4123 行和 4128 行
- 修改: `umask 077` → `umask 022`（2 处）
- 原因: OHOS 的 hmdfs 文件系统在 `mkdir` 时会附加 setgid 位。`umask 077` 创建的临时目录权限为 `drwx--S---`（0700 + setgid），构建进程自身无法在其中写入文件，导致 `config.status` 失败。改为 `umask 022` 后目录权限为 `drwxr-Sr-x`（0755 + setgid），进程可正常写入。这与 a52dec、aalib 等同仓库包采用相同方案。

## 依赖版本

| 软件 | 版本 | 说明 |
|------|------|------|
| OHOS SDK clang | 15.0.x | aarch64-unknown-linux-ohos 交叉编译器 |
| musl libc | 1.2.x | OHOS 系统库 |
| conan | 2.x | 包管理器 |

## 验证结果

### 上游测试
```
make check
```
结果: 上游测试 = 0
- `Makefile.in` 第 323-324 行: `check-am: all-am` / `check: check-am`
- `check` 目标仅重新构建，不执行任何测试
- 无 TESTS、check_PROGRAMS、check-local、test/ 目录、shell 脚本或 CI 配置

### Conan test_package
```
bash test.sh
```
结果: 9 项检查全部通过
1. 生成 input1.mp3 fixture (520 字节)
2. 生成 input2.mp3 fixture (520 字节)
3. mp3wrap 版本横幅验证 ("Mp3Wrap Version 0.5")
4. 合并两个 MP3 → 输出文件 created
5. 输出文件非空 (字节数 > 0)
6. WRAP 索引标记存在
7. ID3v2 头存在 (偏移 0: "ID3")
8. 输出 > 输入总和 (wrap 开销验证)
9. mp3wrap -l 列出两个输入文件名
10. 负测试: 不存在的文件
11. 负测试: 参数不足

### OHOS 二进制验证
```
file mp3wrap       → ELF 64-bit LSB executable, ARM aarch64
readelf -h         → Machine: AArch64, OS/ABI: ARM64
ldd mp3wrap        → /lib/ld-musl-aarch64.so.1
```

## 交付物

| 文件 | 说明 |
|------|------|
| conandata.yml | 源码 URL + SHA256 + 补丁声明 |
| conanfile.py | Conan 2.x 配方 (autotools, OHOS 适配) |
| manifest.yaml | 版本级清单 |
| patches/0001-crc-uint32t.patch | u_int32_t → uint32_t |
| patches/0002-configure-umask-022.patch | umask 077 → 022 |
| test_package/ | 功能测试套件 (test.sh) |

## 注意事项

- mp3wrap 0.5 发布于 2003 年，使用 automake 1.5，源码风格为 2002 年 C 语言。两个补丁均为最小可移植性修复，不涉及任何重构。
- `u_int32_t` 仅出现在 `crc.c:31`（crc.h 中无该类型），补丁只需修改一处。
- 测试 fixture 在运行时程序化生成（MP3 帧头 + 零填充），不提交任何二进制 .mp3 文件，不涉及版权音频内容。
- mp3wrap 的输出格式为 `<basename>_MP3WRAP.mp3`（`mp3wrap.h` 中的 `EXT` 宏），拆分需使用 mp3splt 工具。
