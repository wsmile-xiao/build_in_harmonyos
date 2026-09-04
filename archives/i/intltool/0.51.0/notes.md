# intltool 0.51.0 适配笔记

## 编译环境
- **构建系统**: autotools（纯 Perl 工具集，无原生编译）
- **编译日期**: 2026-09-02
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 1（0001-configure.patch——跳过 XML::Parser 模块检查）

## 编译步骤（conan create 全流程）

```bash
conan create archives/i/intltool/0.51.0 --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 Launchpad 官方发行下载并 strip_root（目录 intltool-0.51.0）。

### 2. 构建（build()）
- 纯 Perl 脚本集合（intltool-update/intltoolize/intltool-extract/intltool-merge/intltool-prepare）
- autotools：configure + make（用 -j1 避免 HMDFS mkfifo 并行问题）
- 0001-configure.patch 跳过 XML::Parser 检查（XS 模块因 HMDFS dlopen 限制无法加载）

### 3. 打包（package()）
- 产物：bin/ 下 5 个可执行脚本 + share/intltool 数据
- 依赖 perl（ohpcd 已发布）

## 上游测试（rule 4）
- 上游有 selftest 套件（tests/selftest.pl + tests/cases/ 46 个用例文件，
  tests/Makefile.am 声明 TESTS = selftest），40 个编号用例
- 真机实测：**40/40（100%）**——selftest exit=0，全部通过
  （运行方式：E337 解释器桥——从 tests/ 目录 `perl selftest.pl`；HMDFS 仅
  拒绝 shebang 直接执行，解释器调用可正常运行）
- 运行时依赖 XML::Parser：以 ohpcd expat 2.7.3 编译 XML-Parser 2.47 +
  PERL5LIB 注入；无 XML::Parser 时 15/40（25 个 XML 类用例失败），
  补齐后 40/40 全部通过
- 适配后：test_package R34 真实执行 intltool-update --version 校验 0.51.0

## 已知限制
- CI 沙箱 XML::Parser XS 模块因 HMDFS dlopen 限制无法加载——configure 检查
  用补丁跳过；运行时以 ohpcd expat 编译 XML::Parser + PERL5LIB 注入解决
---

**编译结束**: 2026-09-02 11:37
**最终状态**: built
