# DRAFT-10251-libnfc-tools-1.8.0-tools-subpackage-identification：`<pkg>-tools` 类第三方库的「非独立上游」识别与适配口径

> Contributor: SunShine_06 | Status: Draft | Updated: 2026-09-16
> Source: libnfc-tools 1.8.0 适配（PR #10251）
> 对应：`knowledge/drafts/DRAFT-10251-libnfc-tools-1.8.0-tools-subpackage-identification.kv`

## 问题

任务清单里出现 `libnfc-tools` / `libmspub-tools` / `libmysofa-tools` / `libnl3-cli`
这类名字，第一步就要回答三个问题，答错会让整条适配路线跑偏：

1. **上游是谁？** 是独立仓库，还是主库源码树里"顺手编出来的"工具集？
2. **源码包从哪拿？** 有没有独立的 `libnfc-tools-1.8.0.tar.gz`？
3. **要不要 `requires` 主库？** 还是自含编（把主库源码一起编进来）？

## 识别：看发行版口径（最可靠）

这类包在 Debian/RHEL/Alpine/SUSE 生态里通常是**主库源包拆出的二进制子包**，
不是独立上游项目。逐个验证三条：

```sh
# ① 上游有没有独立的 -tools 仓库 / release？
#    GitHub API 探测 owner/repo/releases，或看 distro spec 的 Source0
# ② distro 侧是否存在 <主库> 与 <主库>-tools 同源同版本
#    Debian: apt-cache showsrc <pkg>；RHEL: rpm -q --specfile 的 Source0 + %package tools
# ③ 上游源码树里是不是同一份 tarball 的 utils/ + examples/
tar -tzf libnfc-1.8.0.tar.gz | head -20   # 顶层只有 libnfc-1.8.0/
ls libnfc-1.8.0/utils libnfc-1.8.0/examples
```

**libnfc-tools 实证**：无独立上游仓库；交付物 = `libnfc-1.8.0.tar.gz` 里
`utils/`(9) + `examples/`(12) 共 **21 个 CLI 工具**；Alpine/SUSE 同口径。
与 `libmspub-tools`（主库 libmspub 源码树 tools/）、`libmysofa-tools`
（主库 mysofa2json 藏在 BUILD_TESTS 块内）、`libnl3-cli`（发行版 `%package cli`，
Source0 与 libnl3 同一 tarball）同属一类。

## 适配口径：两条路线，按依赖是否已发布决定

| 路线 | 判据 | 配方写法 | 仓内先例 |
|------|------|---------|---------|
| **依赖主包型** | 主库**该版本**已在制品仓 | `self.requires("< 主库 >/< 版本 >")`，package() 只拷 bin/ 等工具产物 | babl-tools←babl/0.1.126；opus-tools←opus/1.5.2.1 |
| **自含型** | 主库未适配或制品仓无该版本 | 下载主库 tarball 自行编译所需目标，不 requires 主库 | libmysofa-tools、libmspub-tools、mupdf-tools |

判据是**双向**的，不是"因为先例自含所以自含"：

- 依赖主包型 ⟹ 主库该版本在 ohpcd（正推成立）；
- 但自含型的先例前提是"主库至今未适配"，若主库**已有**适配只是**版本停滞**，
  不属同构情形 → 优先按 R36 先适配并发布主库，再写 provider 配方
  （`libnl3-cli` 就是这个判定的典型案例）。

> 版本绑定口径：发行版 `%package` 常写死 `Requires: %{name} = %{version}-%{release}`
> （强绑），但技术上子包源码可能对主库版本不敏感（用 tree/blob SHA 比对确认），
> 仓内也**没有**"子包版本 == 主包版本"的硬规矩。

## 拆分包适配要点（自含型/依赖型通用）

1. **手写 Makefile 时的依赖 flags**：工具源码与主库同树，但 conan 里主库是另一个包时，
   `VirtualBuildEnv` **不注入** `AutotoolsDeps` 的 `CPPFLAGS/LDFLAGS/LIBS`——须显式合并
   `AutotoolsToolchain(self).environment()`（方法，要括号）+
   `AutotoolsDeps(self).environment`（属性，不加括号）再 apply。
   详见 `DRAFT-E2186-autotools-deps-missing-dep-flags`。
2. **库内部头**：工具源码可能 `#include` 主库的**内部**头（非 public include），
   需补 `-I<主库源码>/<内部目录>`（libnfc-tools 的 `pn53x-diagnose.c` 需 `-I<src>/libnfc`）。
3. **`config.h` 宏**：别假设工具源码用了 `HAVE_*` 宏——先数一遍
   （`grep -l 'HAVE_' utils/*.c`）。libnfc-tools 的 21 个源文件对 config.h 宏**零使用**，
   因此**不需要** `-DHAVE_CONFIG_H`；反之若上游 `#include "config.h"` 则必须补。
4. **功能特性宏**：POSIX/XSI 接口缺失时补特性宏而非改源码
   （`nfc-relay-picc.c` 的 `fdopen` 需 `-D_XOPEN_SOURCE=600`，等价上游 config.h 的 AC_DEFINE；
   特性宏家族见 `E033`）。
5. **工具包类型声明**：R38 要求 tool 包**双声明**——软件级
   `archives/<l>/<pkg>/commands.json`（`type=tool`）+ 配方 `package_info()` 里
   `bindirs=["bin"]`；只写一个会导致 PF8/L0k 类型判定冲突。

## 验证（真实证据）

- libnfc-tools 1.8.0：21 工具全部编译（`utils/` 9 + `examples/` 12），
  `conan create` EXIT=0，test_package 输出 `uses libnfc 1.8.0` + `ALL CHECKS PASSED`；
- 走**依赖主包型**：`requires("libnfc/1.8.0")`（该版本制品仓可消费，W0 EXIT=0）；
- 上游 6 个 Cutter 用例真机执行 6/6（见 `DRAFT-10251-libnfc-tools-1.8.0-autotools-test-framework-guard`）。

## 适用边界

- **触发面**：任务名形如 `<pkg>-tools` / `<pkg>3-cli` / `<pkg>-utils` 的第三方库；
- **反例**：名字带 `-tools` 但**确实是独立上游项目**（有自己的仓库、release、
  版本节奏）→ 走普通基础适配，别套拆分包口径；
- **反例**：不能仅凭"-tools 后缀"就判定自含型——判据是主库该版本是否已发布（见上表）。

## 关系

- 依赖 flags 子问题 → `DRAFT-E2186-autotools-deps-missing-dep-flags`
- 特性宏子问题 → `E033`（musl 下需显式定义 `_XOPEN_SOURCE`）
- 上游测试子问题 → `DRAFT-10251-libnfc-tools-1.8.0-autotools-test-framework-guard`

## 查重

按 `拆分包` / `非独立上游` / `-tools` / `%package cli` / `自含型` 检索
`knowledge/graph/` 与 `knowledge/drafts/`：命中项均为其他主题（boost 组件拆分、
argp 补齐库等），**无既有"`-tools` 拆分包识别与适配口径"条目** → 本条为新增方法论条目。
