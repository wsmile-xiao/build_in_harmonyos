# mp3check 0.8.7 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile, configure 仅 echo TARGET 空操作)
- 编译日期: 2026-08-30
- 编译器: clang/clang++ (来自 Conan profile, OHOS AArch64 musl 目标)
- 状态: published (conan create CI 全部通过)

## 上游核实

| 项 | 值 |
|---|---|
| 软件 | mp3check 0.8.7 |
| 上游 | Google Code 归档 (https://code.google.com/archive/p/mp3check/) |
| 源码 URL | https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/mp3check/mp3check-0.8.7.tgz |
| sha256 | 27d976ad8495671e9b9ce3c02e70cb834d962b6fdf1a7d437bb0e85454acdd0e |
| 文件大小 | 71629 字节 |
| sha256 交叉验证 | Homebrew Formula/m/mp3check.rb / Debian mp3check_0.8.7-6.dsc (GPG 签名) / PureOS mp3check 0.8.7-6 — 三源一致 |
| License | GPL-2.0-or-later (COPYING 为 GPLv2 文本; 版权声明含 "version 2 or (at your option) any later version"; 与 Debian copyright 文件一致) |

## 上游测试穷举核查 (无正式测试)

mp3check 上游无测试套件。穷举证据如下:

1. **Makefile 目标**: 仅 `all` / `clean` / `strip` / `dist` / `svnclean` / `install` / `usage` 目标, 无 `check` / `test` / `tap` / `regress` 目标。
   - `grep -iE 'check|test|tap|regress' Makefile` → 无匹配。
2. **源码树**: 无 `test*` / `*test*` / `*check*` / `*tap*` 命名文件。
3. **configure 脚本**: 仅 `eval \`grep ^TARGET TARGET\` && echo Configuring && echo done`, 无测试逻辑。
4. **无 CI 配置**: tarball 内无 `.travis.yml` / `.github/workflows/` / `Jenkinsfile`。
5. **主程序仅二进制**: mp3check.cc 的 `main()` 仅解析参数后调用各模式, 无自检/自测代码路径。

因此消费者侧功能测试由 `test_package` 提供 (见 test_package/MANIFEST.yml)。

## 编译步骤

1. 下载源码: `curl -fSL -o mp3check-0.8.7.tgz https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/mp3check/mp3check-0.8.7.tgz`
2. 校验: `sha256sum mp3check-0.8.7.tgz` → `27d976ad8495671e9b9ce3c02e70cb834d962b6fdf1a7d437bb0e85454acdd0e`
3. 提取: `tar -xzf mp3check-0.8.7.tgz` (strip_root=True, 源码根在 mp3check-0.8.7/)
4. 构建: `make -j1 CXX="clang++" ADDITIONAL_CPPFLAGS="-std=c++98"` (configure 为空操作, 跳过; **不传 CC**, 令 Makefile 的 `CC = $(CXX)` 别名使隐式链接规则用 C++ 驱动 `clang++`, 自动链接 `-lc++`/`-lc++abi`)
5. 安装: 复制 `mp3check` → bin/, `mp3check.1` → share/man/man1/, `COPYING` → licenses/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C++17 编译失败 (placement-new 常量表达式) | tstring.cc 在 `new (nul_mem) Rep()` 处使用 placement-new 写入 `static` 缓冲, 现代 clang C++17 视为硬错误 | 经 Makefile 的 `ADDITIONAL_CPPFLAGS` 钩子追加 `-std=c++98` (经 `CPPFLAGS=$(ADDITIONAL_CPPFLAGS)` 注入, 不覆盖上游 `CXXFLAGS=-Wall -W -g`) |
| 2 | Makefile 硬编码 `CXX = g++` | 上游假定 GCC | 命令行 `make CXX="clang++"` 覆盖 (GNU make 命令行赋值优先于文件内赋值) |
| 3 | 并行构建竞态 | 依赖生成规则 `.dep.*` 首次构建时生成, `-j` 高并发可能竞态 | `make -j1` 串行构建 |
| 4 | 无上游测试 | 项目无 check 目标, 无 test 源文件 | 消费者侧 test_package 提供 4 项功能断言 |
| 5 | 无可审计 MP3 fixture | 直接提交未知二进制违反 R7 | test 时从文档化头部字节 `0xFF 0xFB 0x90 0x00` 合成 6 帧最小流 (满足 MIN_VALID=6) |
| 6 | 链接失败: libc++ EH 符号未定义 (`__cxa_*`/`std::length_error`) | 早期 recipe 在命令行传 `CC=".../clang"`, 覆盖了 Makefile 第 11 行 `CC = $(CXX)` 别名; 隐式链接规则 (第 32 行 `$(TARGET): $(OBJ)`) 用 `$(CC)` 链接, C 驱动 `clang` 不自动加 `-lc++`/`-lc++abi`, 致 EH 符号未定义 | **不传 CC**, 令 `CC = $(CXX)` 别名生效, 链接走 C++ 驱动 `clang++` (自动链接 libc++/libc++abi) |
| 7 | test_package generate() 失败: `write() argument must be str, not bytes` | conan 的 `save()` 仅接受 str (文本模式), MP3 fixture 为 `bytes` | 改用 `open(path, "wb").write(bytes)` 直接二进制写入 |

## 源码修改

无需补丁。所有构建问题通过编译器标志与命令行变量覆盖解决。

## 依赖版本

无依赖 (独立 C++ 程序, 仅 libc/libm)。

## 验证结果 (conan create CI 实跑)

```
$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
mp3check/0.8.7: Sources correctly downloaded from
  https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/mp3check/mp3check-0.8.7.tgz
mp3check/0.8.7: RUN: make -j1 CXX="clang++" ADDITIONAL_CPPFLAGS="-std=c++98"
  ... (7 .o 编译 + clang++ 链接成功)
mp3check/0.8.7: Package '6b129b...' built
mp3check/0.8.7 (test package): RUN: "...mp3check" --version
mp3check version 0.8.7
mp3check/0.8.7 (test package): RUN: "...mp3check" -e --show-valid ".../valid6.mp3"
valid6.mp3:
valid audio mpeg stream
mp3check/0.8.7 (test package): RUN: "...mp3check" -e ".../garbage.bin" | grep -q "not an audio mpeg stream"
mp3check/0.8.7 (test package): RUN: "...mp3check" -e /no/such/file/here.mp3 | grep -q "can.t stat file"
=== EXIT: 0 ===
```

CLI 行为实测 (无管道, 真实退出码):

```
$ mp3check --version
mp3check version 0.8.7
(exit 0)

$ mp3check -e --show-valid valid6.mp3
valid6.mp3:
valid audio mpeg stream
(exit 0)

$ mp3check -e garbage.bin
garbage.bin:
not an audio mpeg stream
(exit 1)

$ mp3check -e /no/such/file/here.mp3
/no/such/file/here.mp3:
can't stat file (dangling symbolic link?)
(exit 0, 诊断输出即断言)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan recipe (makefile 构建, 无依赖, 仅传 CXX, ADDITIONAL_CPPFLAGS 注入 -std=c++98) |
| conandata.yml | 源码 URL + sha256 |
| manifest.yaml | 版本级 manifest |
| test_package/conanfile.py | 4 项消费者功能测试 (CLI/正常输入/非法输入/非法路径), fixture 二进制合成 |
| test_package/MANIFEST.yml | 上游测试声明 (无正式测试的穷举证据) |

## 注意事项

- 上游 Google Code 已归档 (read-only), 源码仅通过 Google Cloud Storage 归档下载链接获取; sha256 经 Homebrew/Debian/PureOS 三源交叉验证。
- `-std=c++98` 是必需的: tstring.cc 的 placement-new 模式在 C++17 下为硬错误, 在 C++98 下为可接受扩展。
- **不传 `CC`**: Makefile 第 11 行 `CC = $(CXX)` 将 C 驱动别名到 C++ 驱动; 隐式链接规则 (第 32 行) 用 `$(CC)` 链接。若命令行覆盖 `CC=clang` (C 驱动) 会破坏别名, 链接缺 `-lc++`/`-lc++abi`, 致 `__cxa_*`/`std::length_error` 未定义。令别名生效即可。
- `make -j1`: 依赖生成规则要求串行; 高并发 `-j` 可能竞态 `.dep.*` include 文件。
- 流识别阈值 MIN_VALID=6: 单帧或 < 6 帧被判定为 "not an audio mpeg stream"; test fixture 必须恰好 6 帧。
- test_package 的二进制 fixture (mp3) 须用 `open(path, "wb")` 写入; conan `save()` 仅接受 str。

---
**编译结束**: 2026-08-30
**最终状态**: published (conan create CI 全部通过, OHOS AArch64 musl)
