# pinentry 1.3.2 编译笔记

## 编译环境
- **构建系统**: autotools
- **编译日期**: 2026-05-28
- **编译器**: clang/clang++
- **状态**: built（已知限制：libgpg-error符号缺失阻塞发布）

## 编译步骤记录

### 1. 源码准备
- **源码版本**: pinentry-1.3.2
- **源码格式**: tar.bz2
- **下载地址**: https://gnupg.org/ftp/gcrypt/pinentry/pinentry-1.3.2.tar.bz2
- **构建目录**: ~/builds/pinentry-1.3.2.work
- **原始目录**: ~/builds/pinentry-1.3.2.orig

### 2. 平台适配（补丁应用）

修改了以下文件以适配HarmonyOS：

#### 补丁1: build-aux/config.sub
**问题**: config.sub不识别HarmonyOS平台
**根因**: GNU config.sub缺少HarmonyOS识别规则
**解决方案**:
- 添加`linux-ohos*`到基本OS列表（第134行）
- 添加`ohos-linux`三元组识别
- 添加`ohos*`到OS列表

**验证命令**:
```bash
./build-aux/config.sub aarch64-unknown-linux-ohos
# 输出: aarch64-unknown-linux-ohos
```

#### 补丁2: configure
**问题**: configure libintl检测失败
**根因**: libintl库检测逻辑与HarmonyOS不兼容
**解决方案**: 修改configure脚本绕过libintl检测

#### 补丁3: pinentry/pinentry-emacs.c
**问题**: 编译错误，未定义符号引用
**根因**: 缺少必要的头文件或符号定义
**解决方案**: 补充缺失的头文件和符号定义

### 3. Configure配置

```bash
cd ~/builds/pinentry-1.3.2.work
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
export NCURSES_CFLAGS="-I$HOME/usr/local/include"
export NCURSES_LIBS="-L$HOME/usr/local/lib -lncursesw"
./configure --prefix=/storage/Users/currentUser/usr/local --enable-pinentry-curses
```

**配置成功输出**:
- Build system type: aarch64-unknown-linux-ohos
- Host system type: aarch64-unknown-linux-ohos
- Compiler: clang
- Dependencies detected: libassuan, libgpg-error, ncurses

### 4. 编译构建

```bash
make -j2
```

**编译成功产物**:
- pinentry-curses（主程序）
- pinentry（软链接指向pinentry-curses）

### 5. Staging安装

```bash
make install DESTDIR=/storage/Users/currentUser/test-install-pinentry-1.3.2
```

**安装位置**:
- `/storage/Users/currentUser/test-install-pinentry-1.3.2/storage/Users/currentUser/usr/local/bin/pinentry-curses`
- `/storage/Users/currentUser/test-install-pinentry-1.3.2/storage/Users/currentUser/usr/local/bin/pinentry`

### 6. 测试验证（make check）

pinentry软件无make check目标，跳过测试。

## 问题记录

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | config.sub不识别HarmonyOS | 缺少平台识别规则 | 添加HarmonyOS识别（补丁1） | ✅ 已固化 |
| 2 | configure libintl检测失败 | 检测逻辑不兼容 | 修改configure绕过检测（补丁2） | ✅ 已固化 |
| 3 | pinentry-emacs.c编译错误 | 未定义符号 | 补充缺失定义（补丁3） | ✅ 已固化 |
| 4 | **libgpg-error符号缺失** | 预编译包问题 | 需重编译libgpg-error | ❌ 未解决（阻塞） |
| 5 | **G0验证失败** | clean-verify传递空host参数 | 需修复脚本逻辑 | ❌ 未解决 |

## 问题4详细说明（libgpg-error符号缺失）

### 现象
执行pinentry-curses时报错：
```
Error loading shared library libgpg-error.so.0: (needed by libassuan.so.9)
Error relocating libassuan.so.9: gpgrt_get_syscall_clamp: symbol not found
Error relocating libassuan.so.9: gpg_strsource: symbol not found
...
```

### 根因分析
pinentry依赖libassuan，libassuan依赖libgpg-error。平台预编译的libgpg-error存在以下问题：
1. libgpg-error.so.0未正确链接libintl库
2. 缺少libintl相关符号（如gpgrt_get_syscall_clamp、gpg_strerror等）
3. 这些符号在libintl.h中定义，但libgpg-error编译时未包含

### 影响范围
- 所有依赖libassuan的软件都会遇到此问题
- 包括：pinentry、gnupg、gpgme等GnuPG生态软件

### 解决方案选项

**方案A: 重新编译libgpg-error**
- 核心：编译时正确链接libintl
- 需要：编译libgpg-error源码（版本≥1.49）
- 成本：高（需编译依赖链）

**方案B: 创建libintl-alias.a桥接库**
- 快速：创建wrapper库提供libintl符号
- 问题：违反R6（补丁不应包含生成文件）
- 成本：中（需固化wrapper.c）

**方案C: 接受built状态**
- 本次采用：详细记录问题，等待后续专项解决
- 成本：低（不阻塞交付）

### 本次决策
采用方案C，原因：
1. libgpg-error问题是平台预编译包问题，非pinentry本身
2. pinentry编译成功，产物完整
3. 详细记录可供后续libgpg-error重编译参考
4. 不阻塞本次任务交付时间表

## 问题5详细说明（G0验证失败）

### 现象
执行`ohc-run.py clean-verify`时configure失败：
```
configure: WARNING: invalid host type: []
checking build system type... Invalid configuration `[]': machine `[]-unknown' not recognized
configure: error: /bin/sh ./build-aux/config.sub [] failed
```

### 根因
clean-verify脚本在调用configure时传递了空字符串的host参数（`[]`），导致config.sub失败。

### 影响
G0门禁阻塞，无法升级到published状态。

### 待修复
需修复ohc-run.py clean-verify逻辑，正确传递configure参数。

## 依赖版本

- libgpg-error: 平台预编译版本（存在符号缺失）
- libassuan: 平台预编译（依赖libgpg-error）
- ncurses: 平台预编译

## 验证结果

### Staging验证
```bash
ls -la ~/test-install-pinentry-1.3.2/storage/Users/currentUser/usr/local/bin/
# pinentry-curses: 608896字节
# pinentry: 软链接指向pinentry-curses
```

### 运行验证（失败）
```bash
~/test-install-pinentry-1.3.2/storage/Users/currentUser/usr/local/bin/pinentry-curses --version
# Error: libgpg-error符号缺失
```

### G0验证（失败）
```
G0_CHECK: clean-build-verify
RESULT: FAIL
FAILED_STEP: configure
ERROR: Invalid host type: []
```

### G1-G4验证
```
G1 Binary Integrity: PASS（产物完整）
G2 Functional: FAIL（运行时错误）
G3 Portability: PASS
G4 Archive: FAIL（manifest.yaml缺失，现已补充）
```

## 交付物清单

| 文件 | 大小 | 说明 |
|------|------|------|
| pinentry-curses | 608896字节 | 主程序（staging产物） |
| pinentry | 软链接 | 指向pinentry-curses |
| 0001-build-aux-config.sub.patch | ~2655字节 | 平台识别补丁 |
| 0002-configure.patch | ~889字节 | configure修复补丁 |
| 0003-pinentry-pinentry-emacs.c.patch | ~670字节 | 源码修复补丁 |
| manifest.yaml | 必填 | 版本级元数据 |
| notes.md | 必填 | 编译笔记 |

**预编译包**: 无（G0阻塞，无法制作tar.gz）

## 注意事项

1. **无法发布预编译包**: G0验证失败阻塞门禁
2. **运行时依赖问题**: libgpg-error符号缺失需后续专项解决
3. **后续任务**:
   - 编译libgpg-error（正确链接libintl）
   - 修复clean-verify传递空host参数问题
   - 重新验证G0门禁并制作预编译包

## Git提交信息

- **分支**: feat/pinentry-1.3.2
- **提交**: 仅包含pinentry相关归档文件
- **状态**: built（阻塞发布）

---

**编译结束时间**: 2026-05-28 14:20
**最终状态**: built（已知限制阻塞发布）
**阻塞原因**: libgpg-error符号缺失 + G0验证失败
**解决方案**: 后续编译libgpg-error修复根因