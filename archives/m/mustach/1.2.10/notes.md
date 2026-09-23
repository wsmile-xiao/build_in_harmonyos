# mustach 1.2.10 适配笔记

## 编译环境
- 构建系统: meson（上游双构建系统：Makefile 主 + meson 辅；本配方走 meson）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（OHOS 适配版 conan 2.29.1 + ci/conan/profiles/ohos-aarch64，tool_requires meson/1.11.0）
- 状态: built
- worktree: $HOME/ws/worktrees/mustach-1.2.10 分支 feat/mustach-1.2.10（基线 upstream/main 48d9cee68）

## 任务与 W0/W0b
- 上游确认：gitlab.com/jobol/mustach（作者 José Bollo），tag 1.2.10 存在
  （git ls-remote 实核），tarball SHA256 95a2a351e748db9eeb98f40ba8bfbf010c1c6d2e725d31a3c7e602526d05bf90
  （两次独立下载一致）。
- W0: 核心库（mustach.c + mustach-wrap.c）零外部依赖；JSON 后端 cjson/json-c/jansson
  为可选依赖（上游 auto 探测语义），三者制品仓均已实查在架
  （conan list -r=ohpcd：cjson/1.7.19、json-c/0.17+0.18、jansson/2.14+2.15.1+2.15.1.1）。
- W0b: 无同软件历史归档（archives/_index.yaml 与 archives/m/ 均无 mustach，全新包）。
  语言预检通过（task=cpp, detected=c，c↔cpp 兼容族，milestone=lang_checked）。
- 一手编译探针：设备 clang 直接 -c mustach.c / mustach-wrap.c 通过（零告警）。

## 上游版本勘误
- tag 1.2.10 内 meson.build 的 project version 为 1.2.8（上游未随 tag 递增）；
  Makefile 的 MAJOR/MINOR/REVIS=1.2.10 与 tag 一致，为权威版本。本配方包版本 1.2.10。

## 编译步骤
1. init-build（--allow-unpublished 全新包）+ lang-preflight 通过
2. 配方：meson 配方（tool_requires meson/1.11.0），libs=single、
   cjson/jsonc/jansson=enabled、tool=auto、wrap_mode=nofallback
3. build() 内：meson configure + build；原生环境跑上游工具测试 test1..test8
   （上游 dotest.sh 渲染比对 resu.ref，NOVALGRIND=1，mustach 指向 build 产物）
4. spec 三套件走 Makefile 带参路径在真机采信轮真实执行（克隆 mustache/spec v1.4.1）
5. conan create → conan-verify → finish（见 reports/ 与 .ci-result.json）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson test 的 specs 三条目 PASS 但零覆盖 | test() 注册不带 args，test-specs main() 对空 argv 宽容返回 0（summary 全 0） | 真实 spec 覆盖走 Makefile 带参路径 + mustache/spec v1.4.1 克隆，在真机采信轮执行；注册数与真跑数分开申报（详见 DRAFT-E650） |
| 2 | test6 make test 报 json-c 头/库不可见 | 上游 test6 直编源码并裸 -ljson-c，假定发行版系统前缀；Conan 依赖在私有 package_folder | build() 注入 CPATH/LIBRARY_PATH（取 self.dependencies["json-c"].cpp_info），不改上游文件；json-c 制品为 libjson-c.so.5 共享形态，运行期再加 LD_LIBRARY_PATH（详见 DRAFT-E651） |
| 3 | meson install 在 HMDFS 的符号链接坑（account-utils/1.4.0 先例） | install 目标创建符号链接在 HMDFS 不可靠 | 不调用 meson install，package() 直接从 build 目录收纳 libmustach.a/.so 与 mustach CLI；上游 meson.build 的 library() 未声明 version/soversion，产物无符号链接链 |
| 4 | 上游 Makefile 路径依赖 pkg-config 探测与 install/sed 工具 | 设备/CI 工具差异面大 | 配方走 meson：MesonToolchain 自动指 pkg_config_path 到 generators 目录，PkgConfigDeps 生成依赖 .pc；cjson 包默认生成 cjson.pc 而上游 meson 请求 dependency('libcjson')，在 generators 目录补 libcjson.pc 别名（atk/2.36.0 补 pc 先例） |
| 5 | mustach_mem 等内存渲染接口输出恒空且 size 下溢 | OHOS musl 的 open_memstream 纯 fclose 不回写 *buffer/*size（必须显式 fflush）；tmpfile() fallback 因 /tmp 只读返回 NULL | 平台补丁 0001-ohos-open-memstream-flush-before-close.patch：memfile_close 的 fclose 前补 fflush；设备四象限探针定性（详见 DRAFT-E660） |

## 源码修改
- 仅一个平台补丁：patches/0001-ohos-open-memstream-flush-before-close.patch
  （mustach.c memfile_close 的 fclose 前补 fflush，修复 OHOS musl open_memstream
  纯 fclose 不回写 *buffer/*size 导致的内存渲染输出恒空；见 DRAFT-E660）。
  未修改上游测试与构建文件。

## 依赖版本
- 可选 JSON 后端（编入 libmustach，符号由后端库提供）：cjson/1.7.19、json-c/0.18、
  jansson/2.15.1.1（cpp_info.requires 传播给消费者）。
- 构建工具：meson/1.11.0（制品仓 tool_requires）。

## 交付物形态
- libmustach（static libmustach.a / shared libmustach.so）：core + 三个已启用后端 wrapper 合一（libs=single）。
- mustach CLI（bin/）：tool=auto（第一个启用后端 cjson），静态包含。
- 头文件 include/mustach/：mustach.h、mustach-wrap.h + 三个后端头（消费者
  `#include <mustach/mustach.h>`，与上游 pkg-config Cflags: -Imustach 同形态）。
- commands.json（包级）：mustach CLI 声明（R38/L0k/PF8）。

## 注意事项
- 上游 meson test 对 tool testN 依赖系统 make（find_program('make')）；本配方
  build() 以同款 env（NOVALGRIND=1 + mustach=绝对路径）直接驱动 make test，
  语义与 meson 注册条目一致且逐目录可见。
- 设备 /tmp 只读：test_package 输出文件写当前工作目录（见 test_mustach.c 注释）。

## 验证结果

### 对话 #1（适配会话记录）

```text
任务: feat/mustach-1.2.10（鸿蒙 PC 单端模式）
W0: 上游 tag 1.2.10 实核存在（git ls-remote gitlab.com/jobol/mustach）；
    核心零强制依赖，可选后端 cjson/1.7.19、json-c/0.18、jansson/2.15.1.1 均在制品仓在架
语言预检: lang-preflight 通过（detected=c，milestone=lang_checked）
配方: meson 路线（tool_requires meson/1.11.0），libs=single + 三后端 enabled + tool=auto
试跑: conan create 六轮迭代修复（pc 别名/conf 读取/运行期库路径/open_memstream 平台补丁/消费者测试）
采信轮: conan_verify_round rc=0，干净轮（run_make=13, apply_patch=1），G0-G4/L2/L4/L5 全 PASS
spec: 三套件真机真跑 399/399（cjson/json-c 与官方 ref 逐字节一致；jansson 优于 ref，见 reports/upstream-spec-suites.md）
W3: 本地 CI 模拟通过（L0/L1/L2/L4/L5 pass，Build 1/1 100%）
终态: built
```

详细验证数据见 reports/test-report.md。

---

**编译结束**: 2026-09-22
**最终状态**: built
