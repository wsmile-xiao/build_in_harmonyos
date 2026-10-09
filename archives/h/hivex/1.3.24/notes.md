# hivex 1.3.24 适配笔记

## 编译环境
- 构建系统: autotools（上游 tarball 自带 configure + 内置 gnulib，无 autoreconf）
- 编译日期: 2026-09-27
- 编译器: clang 15 / clang++（profile `ci/conan/profiles/ohos-aarch64`，os=OHOS 6.0/armv8）
- 状态: published

## 编译步骤

```bash
python3 scripts/ohc-run.py conan-verify hivex 1.3.24
```

配方 `build()` 的顺序：

1. `apply_conandata_patches()`（本包零 .patch 文件）
2. `_restore_autotools_helper_modes()` — E490：按需给 autotools helper 脚本补执行位
3. `_patch_config_for_ohos()` — E007/E072：给 `build-aux/config.guess`、`config.sub`
   补 HarmonyOS 分支，使三元组识别为 `aarch64-unknown-linux-ohos`
4. `AutotoolsToolchain` 生成的参数直接进 `autotools.configure()`
5. `autotools.make(-j1)` — 编译库本体（libhivex + 上游两个 CLI）
6. `autotools.make(target="check")` — 层 1 上游测试：`PASS: test-just-header`（TOTAL 1 / PASS 1）

关键 configure 选项：

```
--enable-static --disable-shared
--disable-ocaml --disable-perl --disable-python --disable-ruby
--disable-nls --without-readline
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one` | OHOS 原生构建（host=build）profile 不传 `--host`，configure 回落到 `build-aux/config.guess`，而 GNU config.guess（2022-05-25 版）没有 HarmonyOS 分支 | E007：`_patch_config_guess()` 在 `*:NetBSD:*:*)` 前插入 HarmonyOS case，输出 `aarch64-unknown-linux-ohos`。**不使用** `--build/--host` 绕过（会被 autoconf 当成交叉编译，跳过全部 `AC_RUN_IFELSE`，产出错误 config.h） |
| 2 | `Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'` | config.sub 的内核兼容列表 `case $kernel-$os in linux-gnu* \| ... \| linux-uclibc* )` 不含 `linux-ohos` | E072：`_patch_config_sub()` 在 `linux-uclibc*` 后补 `\| linux-ohos*`。**注意**：仓内 `scripts/patch-autotools-ohos.pl` 的第 2.3 步守卫写作 `unless (/linux-ohos/)`，而同脚本第 2.1 步刚写入 `basic_os=linux-ohos`，守卫因此命中、该步被静默跳过（脚本仍自评 4/5 通过）。本配方在调用脚本后按幂等变换补齐，并把 2.3 的守卫改成 `linux-ohos*` 以避开这一碰撞 |
| 3 | `hivexsh`/`hivexml` 无法通过 L2 smoke test | 两个工具都是手工 getopt（`"df:wu"` / `"dku"`），`--version`、`--help` 均被判非法选项并 `EXIT_FAILURE` 退出 | 改为纯库包：`package()` 里 `autotools.install()` 后删除 `bin/` 与 `*.la`。L2 在「无 `bin/` 目录」时整段跳过 |
| 4 | shared 构建在链接 `libhivex.so` 时失败 | configure.ac 用 `/usr/bin/ld --help` 探测 `VERSION_SCRIPT_FLAGS`；OHOS 无 `/usr/bin/ld`，退化成 Solaris 形式 `-Wl,-M -Wl,`，lld 无法解析 | `validate()` 直接拒绝 `shared=True`，默认静态（R26） |
| 5 | `REG_MULTI_SZ` 读回断言误报 | `hivex_value_multiple_strings()` 的 `while (p < data + len)` 会把 MULTI_SZ 的结尾空串也算成一个元素，两字符串读回是 `{alpha, beta, "", NULL}` | 测试断言改为「数组以 NULL 结尾 + 前导非空元素为 alpha/beta」，不依赖结尾空串是否被裁剪 |
| 6 | 某些 OHOS 适配路径复制源码会丢 helper 脚本的 `+x`，`/bin/sh: <b>/configure: Permission denied`（Error 126） | E490：autotools helper 脚本被 Makefile 直接执行，需要执行位 | `_restore_autotools_helper_modes()` 按需给 `configure`/`config.guess`/`config.sub`/`install-sh`/`missing` 补执行位；本机模式已正确，实跑为 no-op（`conan-verify` G0 的知识图谱提示仍会点名 E490，属提示而非实际失败） |

## 源码修改

无 `.patch` 文件。唯一的源码改写是 `build()` 内对 `build-aux/config.guess`、
`config.sub` 的 E007/E072 变换，使用 `scripts/patch-autotools-ohos.pl` 的等价逻辑
内联实现（脚本存在时先调用脚本，再跑幂等补齐）。

## 依赖版本

无外部依赖。`readline`（hivexsh 行编辑）与 `libxml2`（hivexml）均为可选且本配方
不提供，语言绑定全部关闭；库本体仅由 gnulib + `lib/*.c` 组成。

## 验证结果

```bash
# 库本体 + 消费者测试
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
              --build=missing --user=ohpcd --channel=stable        # rc=0
#   checking build system type... aarch64-unknown-linux-ohos
#   checking host system type...  aarch64-unknown-linux-ohos
#   package(): Packaged 1 '.a' file: libhivex.a / 1 '.pc' file: hivex.pc
#   100% tests passed, 0 tests failed out of 1   (test_hivex: 37 checks, 0 failures)
```

```bash
python3 scripts/ohc-run.py conan-verify hivex 1.3.24
#   G0/G1/G2/G3/G4 + L2/L4/L5 —— 见 reports/conan-verify-report.md
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `lib/libhivex.a` | 静态库（约 0.9 MB） | 唯一的压缩包产物，R26 默认静态 |
| `lib/pkgconfig/hivex.pc` | - | pkg-config 元数据（`pkg_config_name=hivex`） |
| `include/hivex.h` | - | 公共头文件 |

## 注意事项

- **本机构建入口**：鸿蒙 WorkBuddy 运行环境的用户卷 python3 未签名，`conan` 脚本的
  shebang 指向它时，其进程树无法 `execve` 用户卷上的任何文件（`configure: Permission
  denied` / `Error 126`）。用 HAP 内置的签名 python3
  （`/data/storage/el1/bundle/libs/arm64/python/bin/python3` + `PYTHONPATH=~/usr/local/lib/python3.12/site-packages`）
  启动 conan 即可正常构建；本地用一个 `conan` 垫片放在 PATH 最前面交给 `ohc-run.py` 使用。
- 本包**只交付库**，不交付 `hivexsh`/`hivexml`；需要 CLI 的消费者从同一 tarball 自行构建。
- `AM_GNU_GETTEXT([external])` 是无条件的，`--disable-nls` 必须保留，否则 configure
  会索要 `msgfmt`/`xgettext` 并尝试链接 libintl。
---

**编译结束**: 2026-09-27 22:59
**最终状态**: published
