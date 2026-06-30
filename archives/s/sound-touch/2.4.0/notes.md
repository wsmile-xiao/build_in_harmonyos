# SoundTouch 2.4.0 — 编译笔记

## 软件信息

- **名称**: SoundTouch — 音频处理库，用于独立调整音频的节奏(tempo)、音高(pitch)和播放速率(rate)
- **版本**: 2.4.0
- **许可证**: LGPL v2.1
- **构建系统**: autotools (源码包不含 configure 脚本，需先运行 bootstrap/autoreconf 生成)
- **目标平台**: OHOS aarch64 (鸿蒙系统)

## 编译步骤

1. **Bootstrap**: `./bootstrap` (运行 autoreconf，生成 configure 脚本)
2. **HMDFS umask 修复**: `sed -i 's/umask 077/umask 022/g' configure`
   - 原因: HMDFS 文件系统下 autoreconf 生成的 configure 包含 `umask 077`，
     限制性掩码会阻止 config.status 正常创建输出文件
3. **Configure**: `./configure --prefix=$DEFAULT_PREFIX --disable-neon-optimizations`
4. **编译**: `make -j1`
5. **安装**: `make install DESTDIR=$TEST_PREFIX` (暂存) 然后 `make install` (本地部署)

## 关键问题与解决方案

### 问题 1: __powidf2 运行时符号未找到

**现象**: 运行 soundstretch 或加载 libSoundTouch.so 时报错:
```
Error relocating: __powidf2: symbol not found
```

**根因**: OHOS aarch64 的 clang 编译器在 C++ 代码中调用 `pow()` 时，
会生成对 `__powidf2` (软浮点双精度幂函数) 的调用。该符号存在于
OHOS SDK 的 `libclang_rt.builtins.a` 中，而非 libc 或 libm。
默认链接标志 `-lm` 不包含此库。

**解决方案**: 在 Makefile.am 中添加 `-lclang_rt.builtins`:
- `source/SoundTouch/Makefile.am`: `libSoundTouch_la_LIBADD=... -lclang_rt.builtins`
- `source/SoundStretch/Makefile.am`: `soundstretch_LDADD=... -lclang_rt.builtins`

这样将所需的运行时符号静态吸收到共享库和二进制文件中，
`__powidf2` 在库中以本地符号 (t) 形式存在，运行时不再需要外部查找。

**验证**:
```
llvm-nm libSoundTouch.so.1.0.0 | grep powidf
→ 0000000000012338 t __powidf2  (本地符号，已在库内部)
```

**影响范围**: 所有在 OHOS aarch64 上使用 `pow()` 或 `sqrt()` 的 C++ 软件
都可能遇到此问题，需要链接 `-lclang_rt.builtins`。

**知识条目**: E098 (ref: E098)

### 问题 2: config.status 执行失败 (HMDFS umask 077)

**现象**: 运行 `./config.status` 时失败，无法创建输出文件。

**根因**: HMDFS 文件系统下，autoreconf 生成的 configure 脚本在临时目录创建
部分使用了 `umask 077`，此限制性掩码阻止了 config.status 正确创建输出文件。

**解决方案**: bootstrap 之后执行:
```bash
sed -i 's/umask 077/umask 022/g' configure
```
将所有 `umask 077` 替换为 `umask 022`，允许正常文件创建。

**注意**: 此修复为 sed 替换而非传统 diff 补丁，
因为 configure 是生成的文件，不在源码包中分发。
每次重新运行 autoreconf 后都需要重新应用此修复。

**知识条目**: E100 (ref: E100)

### 问题 3: NEON 优化不兼容

**现象**: SoundTouch 的 NEON 汇编优化代码与 OHOS aarch64 工具链不兼容。

**解决方案**: 配置时添加 `--disable-neon-optimizations` 参数。

**知识条目**: E099 (ref: E099)

### 问题 4: 源码包不含 configure 脚本

**现象**: soundtouch-2.4.0.tar.gz 中没有 configure 脚本，
需要先运行 `./bootstrap` (autoreconf) 来生成。

**解决方案**: 编译流程需增加 bootstrap 步骤:
```bash
./bootstrap  # 生成 configure
sed -i 's/umask 077/umask 022/g' configure  # HMDFS 修复
./configure --prefix=... --disable-neon-optimizations
make
```

**知识条目**: E100 (ref: E100)

## 测试结果

项目无自动化测试套件 (`make check` 无实际测试)。
功能测试通过实际 WAV 文件处理验证，详见 test-report.md。

核心功能验证:
- tempo 变换: 输入1秒 → tempo+50% → 输出0.67秒 ✅ (符合 1/1.5 理论值)
- pitch 变换: 输入1秒 → pitch+3 → 输出1秒 ✅ (pitch 不改变时长)
- rate 变换: 输入1秒 → rate+30% → 输出0.77秒 ✅ (符合 1/1.3 理论值)

## 安装产物

| 产物 | 路径 | 大小 | 说明 |
|------|------|------|------|
| libSoundTouch.so.1.0.0 | lib/ | 113152 字节 | 主共享库 |
| libSoundTouchDll.so.1.0.0 | lib/ | 100864 字节 | DLL 包装器 |
| soundstretch | bin/ | 80384 字节 | 命令行工具 |
| SoundTouch.h 等 | include/soundtouch/ | 6 个头文件 | 开发头文件 |
| soundtouch.pc | lib/pkgconfig/ | — | pkg-config 文件 |

---

**编译结束**: 2026-06-08
**最终状态**: published