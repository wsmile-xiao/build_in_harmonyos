# libnova

## 简介
libnova 是一个 C 语言天体力学与天文计算库，提供儒略日/格里历变换、角度与赤道/黄道/地平坐标转换、岁差与章动、大气折射、恒星时与天文时间尺度，以及太阳、月亮、行星（VSOP87）、小行星、彗星位置和物理星历（升落、中天、距角、相位、食）等历表算法。

## OHOS 适配
- 上游 0.16 无官方发布 tarball（SourceForge 仅提供 git tag `v0.16`，files 页面已不可达），源码取自 Debian 官方 orig tarball，已验证与上游 git tag `v0.16` 树逐文件一致（`diff -r` 为空）
- tarball 内不含 `configure` 与 config.guess/config.sub，为 autoreconf 型配方（`autoreconf -fi` 安装 automake/1.18 包提供的这两个脚本），仓库已有同类先例；automake/1.18 的 config.guess（2024-07-27）无法识别本机构建宿主（uname -s = "HarmonyOS"，实测退出码 1），故配方显式传入 `--build/--host=aarch64-unknown-linux-ohos`，其 config.sub 接受该三元组，无需额外补丁
- 补丁 2 个：① 尊重用户 CFLAGS（上游 `configure.ac` 无条件 `CFLAGS=-Wall` 覆盖交叉编译 flag、`src/Makefile.am` 硬编码 `-Wall -O3`，与 Gentoo `libnova-0.16.0-cflags.patch` 同因）② 新增 `.tarball-version`（上游 AC_INIT 经 git-version-gen 读它取版本，tarball 缺失则版本号为 "UNKNOWN"）
- 上游 CMakeLists.txt 要求 `cmake_minimum_required(VERSION 2.6)`，过于陈旧，不采用；统一走 Autotools
- 无第三方编译依赖，仅链接系统 libm；上游在 `src/Makefile.am` 以 `-release 0.16` 控制产物名，共享库为 `libnova-0.16.so.0.0.0`（SONAME `libnova-0.16.so.0`），上游不生成 `libnova.so` 开发符号链接，配方在 `package()` 补建，消费方按常规 `-lnova` 链接即可（pkg-config 名 `libnova`）

## 依赖
- 无编译依赖（仅 libc 数学库 libm）

## 功能验证
```bash
conan create archives/l/libnova/0.16 -pr ci/conan/profiles/ohos-aarch64 -o 'libnova/*:shared=True'
conan create archives/l/libnova/0.16 -pr ci/conan/profiles/ohos-aarch64 -o 'libnova/*:shared=False'
```

上游自带 `lntest` 套件（340 项断言，覆盖儒略日、角度转换、坐标变换、岁差章动、太阳/月亮/行星/彗星位置与升落中天），适配时在 OHOS aarch64 目标上真实执行：316 通过、24 失败（0 跳过）。24 项失败已核实与平台无关（第二条工具链构建逐位一致，非 OHOS 特有回归），均按失败项如实记录；其中仅 5 项有期望值本身的独立证据（3 项章动已被上游 master 提交 7b60adc 修正为与本库计算值一致的 Meeus 值，2 项 Pollux 变换期望与历元正确的 Meeus 22.2 独立归算矛盾），其余 19 项（太阳 3、彗星 9、升落中天 7）无独立重算记录，不改变失败定性。配方对输出做 fail-closed 解析，任何偏离 316/24/340 的漂移都会使构建失败；`test_package` 以有明确来源的天文历表向量（Meeus《Astronomical Algorithms》例题、上游 fixture 中本平台已通过的向量）验证公开 API，容差按各算法的标称精度单独推导，不使用统一宽松 epsilon。

## 参考
- 主页: https://libnova.sourceforge.net/
- 源码: https://sourceforge.net/projects/libnova/ （git tag `v0.16`，实际取 Debian orig tarball，与 tag 逐文件一致）
