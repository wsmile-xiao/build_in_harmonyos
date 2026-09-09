# sassc 3.6.2 适配笔记

## 编译环境
- 构建系统: makefile（sassc 是 libsass 的官方 CLI 封装，单源 sassc.c + Makefile）
- 编译日期: 2026-09-07
- 编译器: clang/clang++（OHOS SDK，libc++）
- 状态: built

## 依赖
- **libsass/3.6.5**（唯一依赖，main/ohpcd 已发布）：静态库 libsass.a + include/sass 头，
  零外部依赖（`requirements(): pass`）。sassc 静态链接 libsass.a → bin/sassc 自包含。
- 链接系统库：-lm、-lc++（OHOS 用 libc++，覆盖上游默认的 -lstdc++）、-ldl

## 构建步骤（conanfile.py build() 内部）
1. source(): 官方 release tarball（github sassc-3.6.2.tar.gz，26KB，不含 libsass）
2. apply_conandata_patches(): 0001-makefile-ohos.patch
3. `make CC=clang CXX=clang++ SASS_LIBSASS_PATH=<libsass 包> LDLIBS="-lm -lc++ -ldl"` → bin/sassc
4. package(): `make install PREFIX=<pkg> DESTDIR=` → <pkg>/bin/sassc + codesign（E077）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接报 `-Wl,-undefined,error: unknown argument` | sassc Makefile 第 17 行硬编码 macOS 专用 `-Wl,-undefined,error`（Darwin ld 才有），OHOS lld（ELF）不认 | 0001 补丁删除该行 |
| 2 | `make` 报 libsass 目录无 Makefile / 重编 libsass | `$(SASSC_EXE): libsass build` —— Makefile 会 `make -C $(SASS_LIBSASS_PATH)` 从源码树重编 libsass（上游并排 clone 布局），但 conan libsass 包只有产物无源码 | 0001 补丁改为 `$(SASSC_EXE): build`（libsass 由 conan 包提供，静态链接 libsass.a） |
| 3 | `make install` 又去 libsass 目录 make install | `install: libsass-install-$(BUILD) ...` | 0001 补丁去掉 libsass-install 依赖 |
| 4 | 链接缺 `libstdc++` / 符号 | Makefile 默认 `LDLIBS += -lstdc++`（静态构建），OHOS 系统无 libstdc++（用 libc++），且 libsass.a 是用 libc++ 构建的 | 命令行长覆盖 `LDLIBS="-lm -lc++ -ldl"` |
| 5 | 可执行文件运行时无法加载 | OHOS 要求二进制 codesign | 移植 glib/dee 的 `_sign_binary()`（binary-sign-tool -selfSign 1） |
| 6 | CLI 工具门禁 R38/L0k | package_type=application 需软件级 commands.json | archives/s/sassc/commands.json（type=tool，参考 strace） |

## 源码修改
- `patches/0001-makefile-ohos.patch`（3 处）：删 `-Wl,-undefined,error`；`$(SASSC_EXE): build`；
  `install:` 去掉 libsass-install。均为构建对接（libsass 由 conan 包提供），不改业务逻辑。

## 测试
- **上游测试 = sass-spec 套件**（外部仓库 github.com/sass/sass-spec，sassc 仓库
  docs/testing/unix-instructions.md 的 `make test`/`make test_spec`）。官方运行器
  `sass-spec.rb` 为 Ruby（OHOS 无 Ruby），用 bash 最小运行器替代实跑。
- **实测**（sass-spec libsass-3.6.3 时代 tag，4604 个 input.scss 用例）：
  - **3094 通过**（2405 普通 + 689 error 类）、**1050 失败**（含 216 个 error
    类 spec 期望失败但 sassc 意外通过；其余多为 rc=65 EX_DATAERR）、296 上游
    options.yml `:todo:` 已知失败跳过、164 无期望输出文件未比对
  - **可比对通过率 3094/(3094+1050) = 74.7%**；全量口径 3094/4604 = 67.2%
  - 按官方口径（lib/sass_spec/util.rb + test_case.rb）：sassc `-t expanded
    --precision 10`（官方默认 precision 10，sassc 默认 5 是差异源）、期望输出优先
    `output-libsass.css`（impl 专属）、归一化折叠连续换行（`gsub(/(?:\r?\n)+/, "\n")`）
  - 早期运行器 error 检测只匹配复数 `*/errors/*`，漏掉单数 `error/` 路径的
    error 类 spec（曾误报"929 无期望输出"）；修正为 `*/errors/*|*/error/*`
    后重跑全量，error 类 spec 计入 error-pass/error-fail 统计
  - 剩余失败多为 rc=65（EX_DATAERR）：libsass 3.6.5 对部分 hsl/color 边界用例
    真实编译报错（如 core_functions/color/hsl/four_args 系列）——真实限制非格式；
    另有少量输出差异
- **test_package R34**：`test_sassc.sh` 真实执行 `sassc` 编译一段 SCSS（变量插值）并
  grep 校验 CSS 输出，1/1 通过（非空壳）。

## 注意事项
- SASS_LIBSASS_PATH 指向 libsass conan 包即可（包内 lib/libsass.a + include/sass 与
  上游期望布局一致），无需复制/改布局。
- 本地 conan create（CI profile ohos-aarch64）验证后再推送。
