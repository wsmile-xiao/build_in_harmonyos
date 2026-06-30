# exempi 2.6.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang/clang++ (OHOS SDK 26.0.0.18)
- 目标平台: aarch64-unknown-linux-ohos
- 状态: published

## 编译步骤

1. 安装依赖: `curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- expat 2.7.1`
2. 修补 configure 脚本（HMDFS mktemp 问题）
3. 修补 config.guess/config.sub（OHOS 平台检测）
4. 运行 configure: `./configure --prefix=$DEFAULT_PREFIX --enable-unittest=no PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH`
5. `make -j1` (441s, 仅警告，无错误)
6. `make install DESTDIR=$TEST_PREFIX` (staging)
7. `make install` (正式安装)
8. 质量门禁: G1-G4 PASS
9. 打包: `ohc-run.py package exempi 2.6.6`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 中 mktemp -d 在 HMDFS 上创建的目录权限为 drwx--S---，阻止文件创建 | HMDFS 不支持 umask 077 + mktemp -d 组合 | 修补 configure 脚本，将 `mktemp -d "./confXXXXXX"` 替换为 `mkdir -p "${TMPDIR:-$HOME/tmp}/conf$$-$RANDOM"` |
| 2 | config.guess/config.sub 不识别 aarch64-unknown-linux-ohos 三元组 | 原始版本不含 OHOS/HarmonyOS 检测逻辑 | 修补 config.guess 增加 __OHOS__ libc 检测，修补 config.sub 增加 ohos-linux/ohos* 支持 |
| 3 | config.sub 中 ohos-linux 条目损坏（重复行） | 手动修补时格式错误 | 修复 ohos-linux case 语句，确保正确结构 |
| 4 | config.sub 中 linux-ohos* 未在 kernel-OS 校验模式中 | 原始 config.sub 只认 linux-gnu* 等模式 | 在 ~1834 行 kernel-OS 校验列表中添加 linux-ohos* |
| 5 | make -j2 失败: llvm-ar 报错 (AIFF_Handler.o: No such file or directory) | HMDFS 不支持 FIFO（make jobserver mkfifo: Operation not permitted），导致并行构建竞争问题 | 使用 make -j1（单线程）避免并行竞争 |
| 6 | /tmp 和管道在 HMDFS 上受限 | HMDFS 文件系统限制 | 使用 $TMPDIR（~/tmp/）替代 /tmp；避免管道重定向到 /tmp |

## 源码修改

- **configure**: 将 mktemp -d "./confXXXXXX" 替换为 mkdir -p "${TMPDIR:-$HOME/tmp}/conf$$-$RANDOM"，避免 HMDFS umask 077 权限问题
- **config.guess**: 添加 __OHOS__ libc 检测逻辑和 HarmonyOS 系统标识
- **config.sub**: 修复 ohos-linux case 语句，添加 linux-ohos* 到 kernel-OS 校验模式，添加 ohos* 到 OS 列表

所有修改通过 `ohc-run.py track-edit` 跟踪记录。

## 依赖版本

- expat 2.7.1 (通过 cmd-pkgs 安装到 ~/usr/local/)
- OHOS SDK 26.0.0.18 (llvm/clang 工具链)

## 验证结果

```bash
$ ~/usr/local/bin/exempi
Exempi version 2.6.6
exempi { -h | [ -R ] [ -X ]  [ -x [ -p ] ] ... } <files>

$ file ~/usr/local/bin/exempi
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ file ~/usr/local/lib/libexempi.so.8.1.6
ELF shared object, 64-bit LSB arm64, not stripped

# 质量门禁: G1 ✅4 ⚠️0 ❌0 | G2 ✅0 ⚠️1 ❌0 | G3 ✅1 ⚠️1 ❌0 | G4 ✅0 ⚠️0 ❌0 | Verdict: PASS
```

## make check 结果

`make check` 未执行（需要 boost 单元测试库，OpenHarmony SDK 不提供）。configure 时已通过 `--enable-unittest=no` 禁用单元测试。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| exempi-2.6.6-ohos-aarch64.tar.gz | 10168KB (~10MB) | 主交付包（含 exempi 二进制、libexempi 共享库/静态库、头文件、pkg-config） |
| exempi-2.6.6-ohos-aarch64-debug.tar.gz | 1331KB | 调试符号包 |

## 注意事项

- exempi 不支持 --version 标志（使用不带参数运行显示版本），G2 有一项警告
- HMDFS 文件系统不支持 mktemp -d 的 umask 077 权限模式，configure 脚本必须修补
- HMDFS 不支持 FIFO（make jobserver），必须使用 make -j1 单线程编译
- 依赖 expat，需要设置 PKG_CONFIG_PATH 才能正确 configure
## 对话记录

### 第一轮对话 (2026-05-28)
- AI: 开始编译 exempi 2.6.6，初始化构建环境
- AI: 下载源码包 exempi-2.6.6.tar.bz2 (3723877 bytes)
- AI: 安装依赖 expat 2.7.1 (通过 cmd-pkgs)
- AI: 发现 configure 中 mktemp -d 在 HMDFS 上创建目录权限异常 (drwx--S---)
- AI: 修补 configure，将 mktemp -d 替换为 mkdir -p + $TMPDIR
- AI: 修补 config.guess，添加 __OHOS__ libc 检测
- AI: 修补 config.sub，修复 ohos-linux 三元组
- AI: configure 成功，make -j1 成功 (441秒)
- AI: make install 成功，二进制和库文件正常
- AI: 首次 finish → 状态 "built" (缺少 test-report.md 和 .knowledge-done)

### 第二轮对话 (2026-06-01) - REWORK
- AI: 修正 manifest.yaml，添加 --build=aarch64-unknown-linux-ohos 到 configure_options
- AI: 修正 sha256 校验和为空的问题
- AI: 修正 tar_format 从 tar.gz 改为 tar.bz2
- AI: 重跑 G0 clean-verify → 通过！configure/make/install 全部成功
- AI: G1-G4 质量门禁全部通过
- AI: finish 因 test-report.md 缺失和 .knowledge-done 缺失降级为 built

### 第三轮对话 (2026-06-01) - 补充
- AI: 执行真实功能测试
  - exempi -h 输出版本号和使用说明 ✅
  - file 检查二进制/库 ELF 格式 ✅
  - pkg-config --modversion 输出 2.6.6 ✅
  - 编写 C API 测试程序，验证 xmp_init/xmp_new_empty/xmp_set_property/xmp_get_property ✅
  - 61 个导出符号确认 ✅
- AI: 创建 test-report.md (完整测试报告)
- AI: 创建 README.md (软件说明文档)
- AI: 更新 manifest.yaml (添加 --build 到 configure_options，修复 patch_classification guard)
- AI: 补充 notes.md 对话记录
---

**编译结束**: 2026-06-01 12:00
**最终状态**: published
