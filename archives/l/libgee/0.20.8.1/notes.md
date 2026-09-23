# Adaptation Notes - libgee 0.20.8.1

## Overview
libgee 0.20.8.1 是 0.20.8 的**工程修复版**（R37 修复规则：上游 0.20.8 +
修复后缀 .1，先例 glib/2.84.0.1）。源码仍为上游 0.20.8 官方 tarball
（同 URL / 同 SHA256）。配方相对 0.20.8 仅两处语义改动：version 号、
generate()/build() 三个依赖循环的 package_folder 守卫；其余
（glib/2.84.0 pin、3 个移植补丁、test_package）逐字保留。

## Bug 根因
- Conan 2 对 Skipped binaries 的依赖节点，`dep.package_folder` 为 `None`。
- 真实失效面（2026-09-03 机理修正，以 conan 2.29.1 自包含探针与设备 conan
  缓存配方实证，替代早先"vendor 内嵌"表述）：glib/2.84.0.1 配方仍声明
  `requires("pcre2/10.45")`/`requires("libffi/3.4.4")`，pcre2/libffi 并非被
  内嵌移除；SHARED 库（glib shared=True）把 STATIC 子依赖（pcre2/libffi，
  shared=False，静态链入自身）的 require 向下游传播时 libs=False——当该
  SHARED 库二进制来自 Cache/Download（不参与本次构建，Conan 不展开它）时，
  其 STATIC 子节点被标记 Skipped binaries：节点仍在图中但 binary=Skip、
  package_folder=None（granite-6.2.0 ci-run2/ci-run3 实证：glib 为 Cache，
  pcre2/libffi/xz/graphite2 被 Skip）。
- libgee/0.20.8 配方 generate() 有两个、build() 有一个
  `for dep in self.dependencies.values():` 循环，均直接解引用
  `dep.package_folder`（`os.path.join(dep.package_folder, ...)` /
  `dep.cpp_info` 前无判空），未设防 → 直接 `TypeError` 崩溃
  （granite-6.2.0 run 的 CI 实测，conan create 在 generate()/build() 阶段崩）。

## 触发场景
granite conanfile 顶层以 `force=True` 声明 glib/2.84.0.1 统一全图
（解决 libgee→glib/2.84.0 与 gtk→glib/2.84.0.1 的版本 pin 冲突），
libgee 的依赖闭包随之出现 pcre2/libffi Skipped binaries。触发条件是该图
形态（SHARED×STATIC 混合 + 中间 SHARED 节点二进制处于 Cache/Download）：
**全新环境全链源码构建反而不触发**——Build 节点会展开其直接依赖，STATIC
子依赖被 require、有真实 package_folder（本包独立 CI 全链源码构建即例证，
守卫在该图形态下为必要防御、在全新全链构建中为防御性执行）。缺陷因此
潜伏到首个命中形态（granite-6.2.0 消费图，glib 二进制为 Cache）才暴露。

## 修复方式
1. conanfile.py 行 21：`version = "0.20.8"` → `version = "0.20.8.1"`。
2. 三个循环的 for 行后逐字插入同一 5 行守卫块（3 行注释 +
   `if not dep.package_folder:` + `continue`）：
   - generate() cflags/ldflags 注入循环（新文件行 54-58）
   - generate() PKG_CONFIG_PATH/PATH/LD_LIBRARY_PATH 注入循环（新行 66-70）
   - build() 依赖 *.la 清理循环（新行 109-113）

   守卫对正常依赖（package_folder 非空）零行为变化；diff 相对 0.20.8
   为 3 处纯插入共 15 行 + 版本号，0 删改。
3. conandata.yml 仍指上游 0.20.8 归档（nju 镜像 URL + 原 SHA256，
   照 glib/2.84.0.1 先例：conan 包名/版本只取 conanfile，source() 按
   conandata URL 下载，无校验障碍）。
4. glib pin 保持 2.84.0 不动（最小修复）：本包自身 graph 的依赖均有真实
   package_folder，守卫为防御性；若本包升 pin 至 2.84.0.1 会引入
   zlib/1.3.1.1 等改动全图，消费方 graph 版本冲突由 granite 顶层
   force 统一处理。

## granite 联动
granite 的 conanfile.py 第 74 行是 pin 死的
`self.requires("libgee/0.20.8", ...)`（CI 日志中出现的 libgee/0.20.Z 只是
Conan 对 package_id 的显示缩写，补丁号不进 package_id，并非版本范围）。
因此 granite 需在后续独立 PR 中把 requires 提升到 libgee/0.20.8.1 才能
吃到本修复；本 run 不修改 granite 包目录。

## 上游测试
libgee 上游有真实测试：automake `make check`（gtester 运行 tests/ 的 C
测试套件）。0.20.8.1 配方 build() 末尾 `make check -j1` 真实执行；
libgee 不在 ci/config/no_official_test.txt 豁免清单中 → 本 run
upstream_test 预期 **PASS**（真实执行，非任何豁免）。权威 CI 日志需留存：
- L1a：test_package 执行痕迹（Testing the package）；
- L1c：`make check` 执行痕迹（detail = upstream tests + test_package executed）。

## Build Process（与 0.20.8 一致）
1. 下载上游 sdist `libgee-0.20.8.tar.xz`（nju 镜像，同 sha256）
2. 应用补丁：0001-config.guess、0002-config.sub、0003-configure-umask
3. configure + make -j1
4. make check -j1（gtester，上游测试）
5. make install DESTDIR=package
6. test_package：C 程序调用 GeeArrayList add/get_size

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | version 0.20.8.1 + 三处 package_folder 守卫（相对 0.20.8 仅此改动） |
| conandata.yml | 头注释标注 R37 修复版；sources/patches 与 0.20.8 相同 |
| manifest.yaml | version 0.20.8.1、source 仍上游 0.20.8、knowledge 追加 R37 记录 |
| notes.md | 本文件 |
| patches/0001-0003 | 与 0.20.8 逐字相同（config.guess/config.sub/umask） |
| test_package/ | 与 0.20.8 逐字相同（C 消费端 add/get_size） |

## 注意事项
1. 上游 tarball 已含预生成 .c 与 stamp，切勿用 git archive 替代（git 快照无 .c/stamp，会强制走 vala 模式）
2. akira 0.0.16 依赖 granite（elementary），granite 依赖 libgee → libgee 是最底层依赖
3. 头文件目录为 include/gee-0.8（非 include/），pkg-config 名 gee-0.8
4. 发布 0.20.8.1 后，下游须显式提升 requires 才能吃到守卫修复（Conan 版本 pin 不自动前滚）

## 同版本修复（2026-09-10）：tests 链接闭包显式化（版本号保持 0.20.8.1）

### 问题
官方 CI 中 0.20.8.1 的 tests 链接在 worker 间不确定，两台 worker 两种症状：
一类报 `undefined reference due to --no-allow-shlib-undefined`
（g_libintl_* 等符号族），另一类链接成功但在后续 gtester 阶段失败。
机制结论（reports/builder/builder-report-linkfix.md，探针实证）：lld 15.0.4
（SDK 26.0.0.18）对输入 DSO 的 `--no-allow-shlib-undefined`（exe 默认）检查，
仅当该 DSO 的 DT_NEEDED 闭包可经默认搜索路径解析时执行；凡依赖用户路径
（-L/-rpath/-rpath-link）定位或定位不到时**静默跳过整个文件的检查**。
`g_libintl_*` 七符号的唯一供给者是 glib 包内 `lib/libintl.so.8`
（OHOS musl 无 libintl，glib 以代理库提供；granite
`_augment_glib_intl_pkg_config`、vala CI #26164 同因同款）——它不在 conan
依赖闭包内、也不在 tests 链接行上，符号解析被寄托在"DT_NEEDED 闭包查找"
这一**工具链语义相关 + 存储状态相关**的隐式机制上，跨 worker 语义/存储
差异即失败根源；闭包残缺时产出"链成功但运行不可启动"的产物。

### 修法（generate() 期显式闭包注入，同版本重发）
generate() **第一依赖循环内、`env = tc.environment()` 快照之前**：
1. 每 libdir 追加 `-Wl,-rpath-link,{libdir}`（使 lld 的 DT_NEEDED 闭包
   查找可定位）；
2. 受 `os.path.isfile` 守卫地追加 `{glib}/lib/libintl.so` 绝对路径为
   显式链接输入（probe4 实证：显式输入在任意 lld 语义/搜索路径下均满足
   严格检查；缺文件时走 output.info 观察分支，不劣化于现状）。

关键陷阱（fixA2/fixA2b 实证复现）：`tc.environment()` 快照**之后**追加
extra_ldflags 会被静默丢弃、不落 LDFLAGS——注入必须发生在快照之前。

### 验证证据
- 官方 CI：两台 worker 两种症状（见"问题"），机制由 linkfix 探针矩阵
  （probe1/3/4、r1-r6、e7-e11）实证。
- 6 组隔离 conan create（linkfix-audit：ctrl/fixA/fixB/fixA2/fixA2b/
  fixA2c）全部 rc=0 且 `make check` PASS；fixA2c（granite force 同款
  glib/2.84.0.1 共享图）tests/Makefile LDFLAGS 同时含
  `{glib}/lib/libintl.so` 绝对路径与 `-Wl,-rpath-link`，产物
  libgee-0.8.so 的 DT_NEEDED（gio/gobject/gmodule/glib/libc）与现网成功
  产物逐项一致，零回归。
- conandata.yml / patches / test_package 零改动；glib/2.84.0 pin 不变；
  版本号保持 0.20.8.1（同版本修复，ohpcd 侧旧制品删除后重发，重发需
  权威 CI 完整复验）。

---
**适配完成**: 2026-09-02（0.20.8.1 同版本链接修复：2026-09-10）
**状态**: 候选提交（权威 CI 通过后标 built；conan_verify 通过后标 published）
