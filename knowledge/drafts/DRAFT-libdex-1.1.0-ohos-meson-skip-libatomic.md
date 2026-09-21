# DRAFT — OHOS：meson 跳过 libatomic 查找（libdex 1.1.0）

**来源事件:** libdex 1.1.0 适配（执行端 pc1-4，2026-09-10）
**状态:** 草稿（待 promote 审核）
**对应 .kv:** `DRAFT-libdex-1.1.0-ohos-meson-skip-libatomic.kv`

## 问题

在 OHOS PC (aarch64, musl) 上 meson 配置 libdex 1.1.0 时：

```
../src/meson.build:93:21: ERROR: C shared or static library 'atomic' not found
```

`src/meson.build` 对非 darwin/非 msvc 平台无条件执行
`libatomic_dep = cc.find_library('atomic')`，OHOS sysroot 无 `libatomic.*`，
meson 在 **configure 阶段**（而非编译/链接阶段）直接失败。

## 根因

OHOS musl sysroot 不提供 `libatomic.a`/`libatomic.so`。aarch64 的原子操作由 clang
内建指令与编译器运行时（compiler-rt）实现，无需也不存在独立 `-latomic` 库。
上游 meson 项目沿用 glibc/Linux 假设（有 libatomic），在 OHOS 上落空。

> 注意：meson 的 `host_machine.system()` 在 OHOS 上返回 `harmonyos`
> （由 OHOS 适配版 conan 的 MesonToolchain 映射），因此 `!= 'linux'` 分支
> 仍会执行 find_library —— 必须显式排除 `harmonyos`。

## 方案

补丁 0002（`patches/0002-src-meson.build.patch`）：在原有守卫
`host_machine.system() != 'darwin' and cc.get_argument_syntax() != 'msvc'`
追加 `and host_machine.system() != 'harmonyos'`，跳过 find_library 与
`cc.links` 校验。OHOS clang 自带 `__atomic_*` 内建，跳过不影响功能。

## 验证

- `meson setup builddir` 配置通过（不再报 atomic not found）
- `ninja -C builddir` 82/82 目标全绿
- `conan create`（ohos-aarch64 profile）G2 通过，`test-fiber` 等上游测试 12/12 PASS

## 适用边界 / 反例

- **适用**：OHOS 上用 meson 构建且 `cc.find_library('atomic')` 的库
- **反例**：CMake 项目（用 `-DOATPP_LINK_ATOMIC=OFF`，见 DRAFT-oatpp）；真用
  `-latomic` 的架构（如 32 位旧架构）不能跳过
- **与既有知识关系**：DRAFT-oatpp-1.3.1-ohos-libatomic-version-subdir 覆盖
  CMake 侧同根因（OHOS 无 libatomic），本条目是其 meson 工具链互补分支，
  触发工具与修复机制不同，非重复

## 查重记录

- DRAFT-oatpp-1.3.1-ohos-libatomic-version-subdir：同根因（OHOS 无 libatomic），
  方案不同（CMake 选项 vs meson 条件分支），部分覆盖、新增 meson 分支差异
- E063（-Werror）：仅 configure 错误文本含 error 字样，根因不同，未命中
- 无 meson 版 libatomic 跳过条目，新增价值成立
