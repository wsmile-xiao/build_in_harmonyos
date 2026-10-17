# E611: autoconf 与 automake 制品的 perl 依赖互相冲突：宿主 perl 被注入包内 5.42.2 的 PERL5LIB 后加载 Cwd.so 失败

## 基本信息
- **严重度**: 2
- **类别**: autotools, conan, toolchain, perl
- **触发工具 / 阶段**: autoreconf|automake|aclocal / configuration
- **来源**: libprelude 5.2.0 适配（OHOS aarch64，PR 分支 feat/libprelude-5.2.0，Agent LPR5）
- **状态**: 草稿（未进 index.tsv，待主编 `graph promote`）

## 错误特征
```
Can't load '.*perl5/5\.42\.2/.*auto/Cwd/Cwd\.so' for module Cwd|Error loading shared library .*Cwd\.so: Permission denied
```

## 触发条件
- 构建系统: autotools（libtool 递归/内嵌 libltdl）或 conan/Conan 依赖图场景
- 阶段: configuration
- 平台: HarmonyOS OHOS aarch64（clang 15 / musl / HMDFS），Conan 2.29.1 + ohpcd 制品

## 根因分析
autoconf/2.72 制品的 .autoreconf-real shebang 指向包内 perl/5.42.2、并由 buildenv 导出指向该包的 PERL5LIB；automake/1.18 制品的 .automake-real shebang 却写死宿主 /data/service/hnp/bin/perl。profile 的 buildenv 把 /data/service/hnp/bin 前插进 PATH，于是 autoconf/automake 脚本都用宿主 perl（5.42.0）去加载 5.42.2 的 XS 模块 → Cwd.so 加载失败，autoreconf/aclocal/automake 全线崩溃（把 autoconf 也 tool_requires 进图才会触发）

影响范围：所有需要 automake + autoconf 同时自举的 autotools 配方（CI 与本机一致复现）

## 解决方案

### 推荐方案（tool-require-only-automake-libtool-use-host-autoconf）
不要 tool_requires autoconf：宿主 HNP 已提供 autoconf/autoreconf 2.72（与 69/78 既有自举配方口径一致），只 tool_requires automake + libtool，PERL5LIB 里就只剩 automake 自己的模块目录，宿主 perl 自洽。若必须引入 autoconf 制品，则需同时把 PATH 首位指向其配套 perl 包并显式管住 PERL5LIB

### 验证命令
```
conan install --tool-requires=automake/1.18 --tool-requires=libtool/2.5.4 -pr=ohos-aarch64 && grep PERL5LIB <out>/conanbuildenv-*.sh
```

### 落地参考
archives/l/libprelude/5.2.0/conanfile.py

## 关键词
Can't load, Cwd.so, Permission denied, PERL5LIB, autoreconf, automake, HNP perl, autoconf 制品, ABI 不匹配, VirtualBuildEnv
