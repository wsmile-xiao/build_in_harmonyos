# notes.md — pangomm 2.46.5 适配笔记

- 日期：2026-10-08
- 平台：HarmonyOS PC（aarch64, musl, clang 15, target `aarch64-linux-ohos`）
- 构建系统：Meson（上游要求 >= 0.60.0） + Conan 2.29.1
- Profile：`ci/conan/profiles/ohos-aarch64`（host = build = 设备原生）
- 上游源码：https://download.gnome.org/sources/pangomm/2.46/pangomm-2.46.5.tar.xz
  - sha256 `38ca0b050b065de4e3da0c182df657437757063bbf0c4b6c9567ddba019b1d68`（633812 字节，与官方 `.sha256sum` 一致）

## 1. 这是什么

pangomm 是 Pango 的 C++ 绑定。**2.46.x 是 legacy mm ABI 线的末版**：
pkg-config 名 `pangomm-1.4`，依赖 `glibmm-2.4`（glibmm 2.66.x）、`cairomm-1.0`
（cairomm 1.14.x）与 `pangocairo`。它与 2.50.x / 2.56.x（`pangomm-2.48` +
`glibmm-2.68` + `cairomm-1.16/1.18`，sigc++-3.0）是**两条独立 ABI 线**，
头文件/命名空间/`.pc` 名都不同，不能混用。

## 2. 上游依赖（`pangomm-2.46.5/meson.build` 取证）

| 探测 | 版本下限 | 本配方提供者 |
|------|----------|--------------|
| `dependency('pangocairo')` | `>= 1.45.1` | `pango/1.50.14.1.1`（components: pango/pangoft2/pangocairo） |
| `dependency('cairomm-1.0')` | `>= 1.2.2` | `cairomm/1.14.5.1`（pkg_config_name `cairomm-1.0`） |
| `dependency('glibmm-2.4')` | `>= 2.48.0` | `glibmm/2.66.9`（components: glibmm-2.4 / giomm-2.4） |
| `glibmm_dep.get_variable('gmmprocdir')` | — | 配方 `generate()` 追加进 `glibmm-2.4.pc` |

选用 `pango/1.50.14.1.1`（而非 1.50.14.1.1.1/1.56.4）的原因：其 `cairo` 约束为
`1.18.4`，与 `cairomm/1.14.5.1` 的 `cairo/1.18.4` 精确一致，**不引入额外 cairo
override**；且其 `harfbuzz/14.2.0.1.1.1` 在制品仓有可用 binary。

### 2.1 libsigc 版本冲突（本包核心适配点）

- `glibmm/2.66.9` 钉 `libsigc/2.10.8`；`cairomm/1.14.5.1` 钉 `libsigc/2.12.1`。
- Conan 2 无法自动归一化两个精确 pin → `Version conflict`，必须 `override`。
- 归一化到 `libsigc/2.12.1`（sigc++-2.0 线内 SONAME 恒为 `libsigc-2.0.so.0`，
  2.x 内 ABI 稳定），对齐制品仓 `cairomm/1.14.5.1` 已发布 binary。
- **副作用（必须在 PR 说明）**：override 改变 `glibmm` 的 `package_id`，制品仓
  没有该变体的预编译 binary，`conan create --build=missing` 会重建 glibmm
  （与 CI 的 `--build=missing` 行为一致，CI 亦如此）。glibmm 源码取自官方
  GNOME 源（`download.gnome.org`）；本机该源不可达时，经 `core.sources:download_cache`
  用官方 GNOME 镜像（mirror.nju.edu.cn）预取的同一 tarball 兜底，**sha256 与配方
  pin 一致**（`5a026e56...`），未修改 glibmm 的 recipe/conandata。

## 3. OHOS 适配要点（全在配方的 `generate()` / `package()`，不改上游源码）

1. **Meson 二进制注入**：clang 工具链在 `/data/service/hnp/bin`（worker 上未必在
   PATH），meson 对 `ar`/`ranlib` 按裸名探测、`pkg-config` 走 PATH，故把三者
   完整路径写进 meson native 文件。
2. **pc 变量补齐**：上游 `meson.build` 无条件调用
   `glibmm_dep.get_variable('gmmprocdir')`，PkgConfigDeps 只写标准变量 → 追加
   `gmmprocdir=${libdir}/glibmm-2.4/proc`。
3. **组件转发 pc**：上游用 `dependency('pangocairo')`；幂等补 `pangocairo.pc`/
   `pangoft2.pc` 转发文件（三字段齐全，版本从 `pango.pc` 读取）。
4. **extra_defs 工具链**：上游 `tools/extra_defs_gen` 用
   `cpp_compiler.find_library('glibmm_generate_extra_defs-2.4')` 查库，把 glibmm
   libdir 注入 `sharedlinkflags`/`exelinkflags`（`-L`）使其命中。
5. **SONAME 链物化**：OHOS 挂载点禁 symlink，`meson install` 的
   `libpangomm-1.4.so` / `.so.1` 链接可能静默缺失 → `package()` 内对
   `libpangomm-1.4.so.1.0.30` 以 `copyfile` 物化 `.so.1` 与 `.so`（幂等）。
6. **重新签名**：原生 OHOS 上 meson install 改写 rpath，`.so` 需
   `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`
   重签（E135）；否则 OHOS 加载器 dlopen 报 Permission denied。
7. **关掉无关目标**：`maintainer-mode=false`（tarball 已含 `untracked/` 预生成绑定，
   无需 mm-common/gmmproc）、`build-documentation=false`（无 doxygen/dot/xsltproc）、
   `wrap_mode=nodownload`（构建期无网络）。

## 4. 上游测试清点（R51 三步法第一步）

**结论：pangomm 2.46.5 上游没有自动化测试入口，测试用例总数 = 0。**

| 检查项 | 命令 | 结果 |
|--------|------|------|
| meson 是否注册 test() | `grep -rn 'test(' --include=meson.build .` | 7 个 meson.build 全部零命中 |
| meson 是否有测试开关 | `cat meson_options.txt` | 无 `build-tests`/`tests` 选项 |
| tests/ 目录内容 | `cat tests/Makefile.am` | `SUBDIRS =`（空壳，11 字节），无 meson.build、无测试源文件 |
| 上游 CI 是否有可复用套件 | 无 | GNOME/pangomm 无独立测试工程 |

因此不存在"因 HarmonyOS 平台限制被跳过"的上游测试，`upstream_test_command` 为空；
消费者验证由 `test_package/`（L1 + 鸿蒙特有测试）承担，**不能替代**上游测试统计
——本包如实标注上游为 0。

## 5. 验证结果

```sh
conan create archives/p/pangomm/2.46.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="pangomm/*"
# exit=0，干净重建 27s（meson compile 30/30 target，链接 libpangomm-1.4.so.1.0.30）
```

- 消费者 L1（`test.cpp`）：4/4 PASS —— `Pango::init()`、`FontDescription::get_family`、
  `FontDescription::get_size`、`AttrList::change()` 插入 AttrInt 后迭代器段数、版本宏。
- 鸿蒙特有（`test_ohos.sh` + `test_ohos.cpp`）：14/14 + 探针 7/7 PASS —— 平台身份、SONAME 链
  物化、ELF64/AArch64/DYN、SONAME、`.note.ohos.ident`、`.codesign`、7 项 DT_NEEDED、
  无 glibc NEEDED、无系统库 RUNPATH、开发头、`pangomm-1.4.pc` 版本与 Requires、
  运行时 `dlopen(RTLD_NOW)`+`dlsym`+真实调用 `Pango::init()`、阴性对照、包载荷完整。
- 合计自建断言 **25/25**。
- 日志：`.ci_logs/` 与 `reports/test-report.md`。

## 6. 遗留 / 说明

- 版本号沿用上游 `2.46.5`（首次适配，无适配修复后缀）。
- 本包与已存在的 `pangomm-2.46/2.46.5` 同名上游、不同 Conan 包名（本包名
  `pangomm`，与制品仓既有 `pangomm/2.50.1`、`pangomm/2.56.2` 同一包名系列）。
- 未应用任何补丁（`patches_applied: []`），无需 `patches/` 目录。

## 7. 知识库扩展（路径 B）

本次新增知识草稿 1 条（随本 PR 入仓，路径 B / 贡献创新）：

- `knowledge/drafts/DRAFT-24650-conan2-override-dep-rebuild-source-cache-fallback.kv` + `.md`
  - 主题：**conan 2 `override` 会改掉被覆盖依赖的 `package_id`** → 制品仓 binary 失配
    （graph 节点 `binary: Missing`）→ `--build=missing` 回落源码重建；当该依赖 conandata
    只有官方源且本机不可达时（`Error in source() method … Connection reset by peer`），
    用 `core.sources:download_cache` + **官方镜像**按 sha256 预取同一 tarball 兜底
    （不修改依赖的 recipe/conandata）。
  - 增量点：已有知识（E538 / DRAFT-13572-*）覆盖"依赖链解析 / ABI 线选型 / override 到哪个版本"，
    本条覆盖其**相邻环节**——"override 之后依赖必然重建，源码如何合法取得"。
  - 官方相似度工具（`ohc-run.py draft-review`）比对正式条目：最高相似 E538 = 0.20，建议 `create`。

## 8. AI 检视意见处置（PR !15064）

| 意见 | 级别 | 处置 |
|------|------|------|
| `test_ohos.cpp` 失败分支 `dlerror()` 被调用两次（首次读取即清除错误状态，第二次返回 NULL → `%s` 收到 NULL 是 UB，且丢失真实错误文本） | P2 | **已修复**：改为 `const char* dlsym_err = dlerror();` 取一次后打印 |
| `test_ohos.cpp` 中 `check(true, "calling Pango::init() ...")` 为恒真断言（测试有效性） | P3 | **已修复**：删除恒真项，改为**阴性对照**——对不存在符号 `dlsym` 必返回 NULL 且 `dlerror()` 置错；`Pango::init()` 保留为真实执行（不再计数） |
| `test_ohos.sh` 断言 9（RUNPATH）在无 RUNPATH 时恒真 | P3 | **已改进**：输出实测观测值（`observed runpath-bearing files: N/3`）；新增末尾 `PASS == 14` 计数自校验，杜绝静默跳过 |
| `test_ohos.sh` 中 `PASS` 计数未被使用 | P3 | **已修复**：末尾断言 `PASS == 14` |

修复后复验：`conan test` rc=0，消费者 4/4 + 鸿蒙特有 14/14 + 探针 7/7（合计 25/25）。
---

**编译结束**: 2026-10-09 11:05
**最终状态**: built
