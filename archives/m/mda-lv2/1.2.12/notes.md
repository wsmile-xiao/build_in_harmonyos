# mda-lv2 1.2.12 适配笔记

## 编译环境
- 构建系统: meson（>= 0.56.0）
- 编译日期: 2026-09-20
- 编译器: clang/clang++（OHOS hnp 工具链，本机即 OHOS arm64 PC）
- 状态: built

## 编译步骤

本机（os_build == os_host == OHOS）原生构建，profile 为 `~/.conan2/profiles/ohos-aarch64`：

```bash
export PATH="$HOME/.local/bin:$HOME/usr/local/bin:$PATH"   # conan/meson/ninja + pkg-config/readelf
conan create archives/m/mda-lv2/1.2.12 --profile:host ohos-aarch64 --profile:build ohos-aarch64
```

配方要点：

1. **依赖**：仅 `lv2/1.18.11-git`（仓库已有二进制，R35 已验证）。上游
   `dependency('lv2', version: '>= 1.16.0', include_type: 'system')` 经
   pkg-config 发现——配方用 `PkgConfigDeps` 生成 .pc，否则 meson 报
   "Run-time dependency lv2 found: NO"。
2. **安装布局**：`tc.project_options["lv2dir"] = "lib/lv2"` → 全部 36 个
   插件 .so + 46 个 TTL（manifest.ttl + 36 插件数据 + 9 presets）安装至
   `lib/lv2/mda.lv2/` 单一 bundle。
3. **native file 注入**：OHOS 沙箱下 meson 经 PATH 找不到 clang/clang++/ar
   （sord 先例），generate() 末尾改写 `conan_meson_native.ini` 注入绝对路径。
4. **本机构建不设 sys_root**：MesonToolchain 默认生成的 native file 含
   `[built-in options] sys_root = <sysroot>`（跨编场景），本机构建时该值
   会拼坏 pkg-config 的 `-isystem` 头搜索路径（exploration 实测：
   `fatal error: 'lv2/atom/atom.h' file not found`）——sherlock.lv2 同款
   先例，配方不设 sys_root 即可。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson configure 报 `lv2/atom/atom.h not found` | native file 设 sys_root 后，pkg-config 传入的 `-isystem<sysroot>/storage/...` 路径被拼坏 | 本机构建不设 sys_root（跨机构建才需要） |
| 2 | `Run-time dependency lv2 found: NO` | meson setup 未经 PKG_CONFIG_PATH 找到 conan 生成的 lv2.pc | 配方 `generate()` 用 `PkgConfigDeps` 生成 .pc（Meson 工具自动接管 pkg_config_path） |
| 3 | dlopen 插件后 instantiate/run 段错误（exit 139） | wrapper.cpp 的 `lvz_instantiate` 遍历 `features[i]`，宿主传 NULL 指针即崩 | 宿主必须传 **NULL 结尾的 features 数组**（`{NULL}`），LV2 规范要求；已沉淀知识草稿 `DRAFT-mda-lv2-1.2.12-lv2-host-contract-features-null-array` |
| 4 | 上游 lint 测试三个中两个不可运行 | autoship/lv2lint 在本机 OHOS 环境无法获取（取证见"上游测试"节） | REUSE 装工具真实执行通过；autoship/lv2lint 留多途径失败证据；上游本无 DSP 功能测试，36 模块由构建期编译 + test_package dlopen 验证 |

## 源码修改

无补丁。上游 meson.build（cpp_std=c++11）在 OHOS clang 15 下直接编译通过，
36 模块全量构建零告警。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| lv2 | 1.18.11-git | 头文件 + pkg-config（armv8/Release/OHOS 6.0） |

## 上游测试

上游 meson 共定义 **3 个测试**，全部由 `-Dlint=true` 门控（默认 false，因此
`conan create` 默认轮次不注册任何测试）；上游**没有** DSP 功能/单元测试：

| # | 测试 | suite | 真实执行结果 |
|---|------|-------|--------------|
| 1 | REUSE（licensing 元数据检查） | data | **真实执行通过**：pip 装 `reuse 6.2.0` 后，`meson setup -Dlint=true -Dtests=auto && meson test` → `1/1 data - mda-lv2:REUSE OK`；直接 `reuse --root . lint` 亦 rc=0（137/137 文件含版权与许可信息） |
| 2 | autoship（release 元数据检查） | data | **环境限制无法运行**：`pip install autoship` → `No matching distribution found`（社区源与 pypi.org 均无）；drobilla.net tarball 404；`git+https://gitlab.com/drobilla/autoship.git` → `Authentication failed`；gitlab archive 接口被 Cloudflare 拦截（返回 HTML） |
| 3 | lv2lint（插件 URI/TTL 静态检查） | plugins | **环境限制无法运行**：`-Dlint=true -Dtests=enabled` 下 meson setup 一手报错 `ERROR: Program 'lv2lint' not found or not executable`（bexp3 日志留档）；源码获取 403（gitlab）/404（github 无此仓库） |

计数：上游测试总数 3 / 真实执行 1（REUSE，通过）/ 环境限制 2（autoship、
lv2lint，均为宿主工具缺失且全部获取途径失败，证据见上）。`tests=auto` 模式
下 meson 对缺失工具静默跳过注册（`find_program(required: feature-auto)`），
故 `meson test` 仅执行 REUSE 一项——这不是选择性跳过，而是本环境可执行集
的真实上界。36 个插件模块的正确性由构建期全量编译 + test_package 三级
验证（ELF 结构 / bundle 布局 / 真实 dlopen 生命周期）覆盖。

## 验证结果

```bash
# conan create（ohos-aarch64）全链路：
#   36 插件 .so + 46 TTL → lib/lv2/mda.lv2/
#   test_package: ELF64/AArch64/NEEDED/RPATH 逐插件校验 36/36 PASS
#   bundle 结构校验（manifest.ttl 36 URI + 9 presets + 36 .ttl）PASS
#   真实 dlopen 生命周期验证（TestTone instantiate+run 480 帧+cleanup）PASS

# 抽样 readelf（TestTone.so，全部 36 个同构）：
#   Class: ELF64 / Machine: AArch64 / SONAME: TestTone.so
#   NEEDED: libc++_shared.so, libc.so（无 rpath 依赖）
#   无 RPATH/RUNPATH（正确：插件由宿主显式路径 dlopen）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/lv2/mda.lv2/manifest.ttl` | bundle 清单（36 插件 URI 声明） |
| `lib/lv2/mda.lv2/<Plugin>.so` × 36 | 插件模块（ELF64/AArch64，导出 lv2_descriptor） |
| `lib/lv2/mda.lv2/<Plugin>.ttl` × 36 | 插件端口/参数描述 |
| `lib/lv2/mda.lv2/*-presets.ttl` × 9 | 预设（DX10/Detune/EPiano/JX10/Leslie/Piano/Splitter/ThruZero/Vocoder） |
| `licenses/` | GPL-2.0-or-later.txt + 0BSD.txt + MIT.txt |

## 注意事项

1. **宿主必须传 NULL 结尾 features 数组**：wrapper 的
   `lvz_instantiate` 对 `features[i]` 做 for 遍历（LV2 规范约定数组以
   NULL 结尾），传 NULL 指针会在第一个 host feature 查询时崩溃。LV2
   宿主（如 Carla/JALV）本身遵守规范，此坑只影响手写加载代码/测试探针。
2. 插件 URI 前缀 `http://drobilla.net/plugins/mda/`（如
   `.../mda/TestTone`），`name_prefix: ''` 使模块文件名为 `Ambience.so`
   等（无 lib 前缀）。
3. `dev=true` 才会构建 lvz 开发工具（默认关闭，本配方未开启）。
4. 上游 meson `project()` 无 C 语言——纯 C++ 项目（`['cpp']`），lvz
   wrapper 以 `-DPLUGIN_CLASS=mda<Name>` 宏实例化每个插件。
