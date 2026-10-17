# OHOS Conan profile 体系：CI 集成、host/build 分层、`-s:b` 边界与产物/cpp_info 校准

> 草稿（DRAFT）— 来自 OpenHarmony 6.0 公共 SDK + OHOS 适配版 Conan 2.29.1 的本地交叉验证环境
> 搭建与真实配方（libsigc 3.6.0、zlib 1.3.2 等）实测；并与仓库 `ci/conan` 的官方 CI 写法对照。
> 与 `.kv` 同 stem 配对，字段见 `knowledge/drafts/DRAFT-ohos-conan-profile-system.kv`

## 问题

同一套“OHOS aarch64 交叉构建”在本机与 CI 上表现完全不同，且失败信息互相矛盾：

1. 本机照抄 CI 的 `-pr:h=<ohos> -pr:b=<ohos>` 后，meson 报
   `binary or interpreter not executable`（sanity check 试图执行 aarch64 二进制）。
2. `os=OHOS` 偶发被 conan 直接拒绝：`Invalid setting 'OHOS' is not a valid 'settings.os' value`。
3. 某些配方编译“成功”，但包内对象实际是 x86_64（`Machine: Advanced Micro Devices X86-64`），
   直到链接别人时才报 `incompatible with aarch64linux`。
4. 消费者 `test_package` 链接通过，但某个组件库其实从未被链接（组件化配方的 `cpp_info.libs` 口径问题）。

这四类都源自 profile 体系本身，而不是单个库的兼容性。

## 根因

### 1. CI 是“设备原生构建”，本地是交叉构建

仓库 `ci/conan/build_and_test.sh` 固定：

```zsh
PROFILE="${CONAN_PROFILE:-ohos-aarch64}"
PROFILE_FILE="$REPO_ROOT/ci/conan/profiles/$PROFILE"
conan create ... -pr:h="$PROFILE_FILE" -pr:b="$PROFILE_FILE"
```

CI worker 本身就是鸿蒙 PC（aarch64），所以 host 与 build 共用一个 profile 是**原生构建**，语义正确。
在 x86_64 宿主机上照抄，conan 判定 `host==build` → 不设 `CMAKE_CROSSCOMPILING` → meson 的
sanity check 直接执行 aarch64 二进制 → `binary or interpreter not executable`。

### 2. `settings.yml` 缓存会“卡住” `os=OHOS`

conan 首次运行会把 `settings.yml` 缓存到 `~/.conan2`。升级到含 `os: OHOS` 的适配版后，
旧缓存没有该枚举；`setup.sh` 因此先探测再删除重建：

```zsh
# conan caches settings.yml on first run; if conan was upgraded (e.g. OHOS
# adaptation added), the cached file may lack the OHOS enum; delete to regenerate.
```

### 3. 构建上下文必须是 Linux（`-s:b os=Linux` 边界）

本地验证的正确写法是：

```bash
conan create . -pr:h=ohos-aarch64-run -pr:b=default --build=missing
```

`default` 就是宿主 Linux 的 profile（`os=Linux`）。只有**确实存在 OHOS 构建上下文工具链**
（例如为 OHOS 准备的 `tool_requires`）时才应写 `-s:b os=OHOS`。把 OHOS profile 塞给 `-pr:b`，
会让 meson/cmake/代码生成器这些**构建期工具**也被当成 aarch64 目标产物，在 x86_64 上不可执行。

### 4. 产物与元数据都需要“再校准一次”

- `[buildenv]` 不会自动作用于 conanfile 里的 `self.run()`（2.29.1 实测），宿主进程环境会泄漏。
  若不把裸名 `CC/CXX/ar` 指向交叉工具链，就会静默产出“被标成 aarch64 的 x86_64 产物”。
- 组件化配方（`cpp_info.components` 非空）的**包级** `cpp_info.libs` 不是组件 libs 的并集；
  CMakeDeps 消费的是组件级数据，只用 `{deps.cpp_info.libs}` 聚合会漏库。

## 五套 profile 的分工

| profile | 相对基准的差异 | 用途 |
|---|---|---|
| `default` | 宿主 Linux x86_64 | **只作 `-pr:b`**（构建上下文） |
| `ohos-aarch64` | SDK clang 15 + sysroot + SDK cmake 3.28.2 | 纯交叉构建，与官方语义一致 |
| `ohos-aarch64-run` | + `CMAKE_CROSSCOMPILING_EMULATOR`（qemu） | 本地默认：动态链接 + qemu 跑测试 |
| `ohos-aarch64-static` | + `tools.build:exelinkflags=["-static"]` + emulator | 动态运行根跑不动时的兜底 |
| `ohos-aarch64-local` | 静态 + 显式 `-L<ohos-runroot>` | 需要指定运行根时 |

共同点：`[conf]` 里 `tools.build:compiler_executables` 指向
`aarch64-unknown-linux-ohos-clang`，`tools.build:sysroot` 指向 SDK sysroot，
`tools.cmake:cmake_program` 指向 SDK 自带 3.28.2（宿主 cmake 3.22 无 `Platform/OHOS.cmake`），
`[buildenv]` 固定 `CONFIG_SHELL=/bin/bash` 与裸名 `CC/CXX/AR/RANLIB`。

## 最小修复 / 验证

```bash
# 1) 交叉构建 + qemu 执行测试
conan create . -pr:h=ohos-aarch64-run -pr:b=default --build=missing

# 2) 产物架构校准（不要只看包名）
file "$PKG/lib/"*.a | grep AArch64
readelf -h ./test_binary | grep Machine      # 期望 AArch64

# 3) 只做纯构建时
conan create . -pr:h=ohos-aarch64 -pr:b=default --build=missing
```

实测：`libsigc/3.6.0` 本地 `conan create`（host=`ohos-aarch64-run`，build=`default`）EXIT=0，
上游 meson 测试 41/41 通过；同一配方若把 build 也换成 OHOS profile，meson 立即
`binary or interpreter not executable`。zlib 1.3.2 的包内对象 `Machine: AArch64`。

## 禁止策略

- 禁止把 OHOS profile 用作 `-pr:b`、或用 `-s:b os=OHOS` 去“让 CI 命令在本机也能跑通”。
- 禁止用宿主 `cmake`（缺 `Platform/OHOS.cmake`）或裸名 `cc/c++` 替代交叉工具链。
- 禁止把“包级 `cpp_info.libs`”当成组件化包的全部导出库来做聚合校验。
- 禁止在没真正执行测试的情况下声称“测试通过”（单 profile host==build 只能做纯构建）。

## 适用边界 / 反例

- 适用于 x86_64（或非 aarch64）宿主上做 OHOS 交叉构建/本地预验证的配方与 CI 包装。
- 在鸿蒙 PC 真机（原生构建）上，CI 的单 profile 写法是正确且推荐的，不要照搬“必须拆 host/build”。
- `ohos-aarch64-run` 用的是“替代 musl 运行根”，与设备运行时仍有差异；最终结论以官方 CI/真机为准。

## 查重（七轴）

- `exact_duplicate`：否 — 图谱无“OHOS Conan profile 体系 / host-build 分层”条目
- `causal_duplicate`：否 — 与并行 PR #13821（`feat/knowledge-linux-x86-ohos-cross-toolchain`，主机侧工具链搭建）
  话题相邻，但那条解决“设备路径在主机不存在”，本条解决“profile 选型与构建上下文边界”
- `trigger_overlap`：部分 — 触发词 `os=OHOS`、`Platform/OHOS.cmake`、交叉工具链同族
- `solution_overlap`：部分 — 都涉及 profile `[conf]`，但本条核心是 host/build 拆分与聚合口径
- `combination_novelty`：有 — 四类 profile 问题在同一条目内闭环，并给出五 profile 分工表
- `boundary_novelty`：有 — 明确 `-s:b os=Linux`（宿主编译）与 `-s:b os=OHOS`（OHOS 构建上下文）的界线
- `test_migration_novelty`：有 — 把“必须真机才能验证”的既有假设改为“host=OHOS / build=Linux + qemu 真实执行”

## 相关

- `similar_to`：E012、E053、DRAFT-elfio-3.9-conan-profile-relative-path-shadowing、
  DRAFT-autotools-config-sub-silent-ohos-triplet、DRAFT-ohos-gotoblas-cross-silent-skip
- 并行工作：PR #13821（`feat/knowledge-linux-x86-ohos-cross-toolchain`，尚未合入图谱）沉淀
  “主机侧交叉工具链搭建”；本条与其互补——那条解决“设备路径在主机不存在”，
  本条解决“profile 选型与构建上下文边界”（本 PR 不引用未合入条目作为 `similar_to`）。
- `principles`：P-TOOLCHAIN-001（LLVM 工具链）、P-ENV-001（环境变量语义冲突）、
  P-LINKAGE-001（静态库优先）、P-BUILD-001（平台限制降级而非绕过）
