# intltool-debian 0.35.0-20060710.6 适配笔记

## 软件定位

intltool-debian 是 Debian 用 `salsa.debian.org/debian/intltool-debian`
独立维护的 intltool 分支，专门为 RFC822 合规配置文件（如 Debian Debconf
模板 `debconf/templates`）做国际化。产物是 3 个纯 Perl 脚本：
`intltool-extract` / `intltool-merge` / `intltool-update`。

> 注意：与 `archives/i/intltool/0.51.0` 是**不同代码库、不同版本串**，
> 不能当作同一配方的不同版本。

## 编译环境

- **构建系统**: 极简 Makefile（非 autotools/cmake，无 configure）
- **编译日期**: 2026-10-01
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built
- **补丁数量**: 0（纯 Perl 脚本，无原生编译，无需源码补丁）

## 构建要点（conan create 全流程）

```bash
conan create archives/i/intltool-debian/0.35.0-20060710.6 \
  --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 源码获取（source()）
`get()` 从 conandata 声明的 **Debian 官方 pool**
（`deb.debian.org`）下载 `intltool-debian_0.35.0+20060710.6.tar.xz` 并
strip_root。上游官方版本串含 `+`，配方版本号按 conan 规则映射为 `-`。

### 构建（build()）
- 纯 Perl 脚本，无原生编译。`make all` 仅确保脚本可执行（上游 Makefile 同）。
- 上游测试：`make test → prove --verbose t/*.t`，`t/syntax.t` 对 3 脚本各
  `perl -wc`（3 断言）。解释器桥可运行（HMDFS 仅拒 shebang 直执行）。
- 运行时依赖 perl + gettext 工具链（脚本调 xgettext/msgmerge/msgfmt）。

### 打包（package()）
- 3 个脚本装入 `bin/`（脚本自包含，无同目录依赖）。
- **与上游差异**：上游 Makefile install 装 `share/intltool-debian`
  （Debian debconf 专用布局）。OSS 作为通用 i18n 工具，按 Conan 工具型
  约定（R38 commands.json）装入 bin/ 以经 PATH 调用。

### 测试（test_package，R34）
- 3 个 bin 工具存在 + 可执行 + `perl -wc` 语法检查通过。
- 每个工具经 perl 解释器桥执行 `--version`，断言输出含 `0.35.0`。
- 9/9 断言通过。

## 上游测试（rule 4）

- 上游测试：`prove --verbose t/*.t`（t/syntax.t，对 intltool-extract/
  intltool-merge/intltool-update 各跑 `perl -wc`，3 个断言）
- 真机实测：**3/3（100%）**——prove exit=0，全部通过
  （运行方式：perl 解释器桥，从 t/ 目录执行；HMDFS 仅拒 shebang 直接执行，
  解释器调用可正常运行）
- 适配后：test_package R34 真实执行 bin 工具，9/9 = 100%

## 已知限制

- 脚本运行完整 i18n 功能（合并 .po）需运行时 gettext 工具链
  （xgettext/msgmerge/msgfmt）。CI 非交互环境下经 test_package 用
  gettext/0.22.5.1（bindirs=bin，conanrun 注入 PATH）覆盖；脚本自身支持
  `XGETTEXT/MSGMERGE/MSGFMT` 环境变量覆盖默认 `/usr/bin/` 路径。
- 无平台宏/系统 API/原生编译风险——纯 Perl 脚本，无 C 编译器参与。

---

**编译结束**: 2026-10-01
**最终状态**: built