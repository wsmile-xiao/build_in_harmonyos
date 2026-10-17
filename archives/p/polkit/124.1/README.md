# polkit 124.1 — HarmonyOS PC 适配说明

## 1. 软件简介

[polkit](https://gitlab.freedesktop.org/polkit/polkit)（PolicyKit）是 D-Bus 授权策略框架，
应用与服务通过它按系统策略检查权限。上游由四部分构成：`polkitd` D-Bus 系统服务守护进程、
**libpolkit-gobject-1** 客户端库、**libpolkit-agent-1** 认证代理库，以及命令行工具
（`pkcheck`/`pkaction`/`pkexec`/`pkttyagent`）。

- 上游版本：**124**（本包 **124.1** = 124 的适配修复版本；源码与 124 **同源同 sha256**，
  版本后缀按 R37 表示适配修复，用于区分制品仓中的不同配方 revision）
- 上游源码：`https://gitlab.freedesktop.org/polkit/polkit/-/archive/124/polkit-124.tar.gz`
- 源码 sha256：`72457d96a0538fd03a3ca96a6bf9b7faf82184d4d67c793eb759168e4fd49e20`
- 开源许可：**LGPL-2.0**（上游 `COPYING`：GNU Library General Public License Version 2，
  制品内随包分发于 `licenses/COPYING`）
- 构建系统：**Meson**

**为什么需要 124.1**：同仓库的 `polkit/124` 以 `-Dlibs-only=true` 构建，上游在该模式下
**一次性跳过 `polkitbackend`/`polkitagent`/`programs`**，因此只交付 `libpolkit-gobject-1`
与 `polkit-gobject-1.pc`。而图形认证代理（本仓库下游 `lomiri-polkit-agent`，其
`debian/control` 与 CMake 均要求 `polkit-agent-1`）额外需要 **libpolkit-agent-1** 与
**polkit-agent-1.pc**。124.1 在保持 124 全部行为的前提下补出 agent 库。

## 2. 适配范围（打包口径）

- 取**官方源码包**构建（无 fork、无镜像改写）。
- `-Dlibs-only=true` 下产出**两个客户端库**：
  - `libpolkit-gobject-1.so`（与 124 一致，行为不变）
  - `libpolkit-agent-1.so`（124.1 新增）
- **跳过** `polkitd`/`polkitbackend`/`programs`（与 124 完全一致）。
- **不含特权 helper `polkit-agent-helper-1`**：该程序鉴权依赖系统口令数据库
  （shadow `getspnam()` 或 PAM），OHOS (musl-based) libc 两者皆无，详见 §5。
- 产物为库文件，**不含命令行可执行文件** → 按 R38 不声明 `commands.json`。
- 补丁 2 个（见 §3）。

## 3. 构建要点

```bash
conan create archives/p/polkit/124.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="polkit/*"
```

Meson 选项：`-Dlibs-only=true -Dauthfw=shadow -Dintrospection=false -Dtests=true
-Dexamples=false -Dman=false -Dgtk_doc=false`。

| 补丁 | 作用 |
|---|---|
| `patches/polkitagent-libs-only.patch`（新增） | ①`src/meson.build`：`libs-only` 下也 `subdir('polkitagent')`（`polkitbackend`/`programs` 仍跳过）；②`src/polkitagent/meson.build`：特权 helper 的 `executable()` 包进 `if not get_option('libs-only')`，使 libs-only 包只交付库 |
| `patches/mocklibc-ohos-fgetgrent-fgetpwent.patch`（沿用 124） | OHOS libc 头文件缺 `fgetgrent()`/`fgetpwent()`，在 `subprojects/mocklibc` 内本地实现，供上游单测使用 |

依赖：`glib/2.84.0.1`（glib/gobject/gio/gio-unix）、`expat/2.8.2`（构建期私有，
`visible=False`）。两个 `.so` 均经 `llvm-objcopy --remove-section .codesign` +
OHOS `binary-sign-tool` 自签名，动态链接器方可加载。

## 4. 验证结果

| 项 | 结果 |
|---|---|
| 编译（`aarch64-linux-ohos` clang 15.0.4，OHOS SDK 26.0.0.18，CI 同款 profile） | **通过**（`conan create` EXIT=0） |
| 产物：`libpolkit-agent-1.so(.0/.0.0.0)` | 存在，63,872 B，已签名 |
| 产物：`libpolkit-gobject-1.so(.0/.0.0.0)` | 存在，158,080 B，已签名 |
| 产物：`lib/pkgconfig/polkit-agent-1.pc` / `polkit-gobject-1.pc` | 均存在 |
| 产物：`include/polkit-1/polkitagent/*.h` | 6 个头文件（含 mkenums 生成的 `polkitagentenumtypes.h`） |
| 上游测试（`test/` 全量清单 **20 项** = 4 单元用例 + 1 集成用例 + 2 注册脚本 + 2 支撑代码 + 10 夹具；vendored `test/mocklibc/` 不计入） | 单元用例 **4/4 通过（100%）**（`LD_PRELOAD` mocklibc，无需 polkitd/D-Bus）；集成用例 `test-polkitbackendjsauthority` 未运行（本包 `-Dlibs-only=true` 未注册 + 缺 polkitd/D-Bus 系统总线），源码未裁剪 |
| **鸿蒙消费者测试**（`test_package/test_polkit_agent.c`，链接组件 `polkit::agent`） | **通过**：agent 类型名与继承关系校验 + `g_object_new()` 实例化，实测输出 `polkit-agent-1 OK: listener=PolkitAgentListener text_listener=PolkitAgentTextListener` |
| 回归测试（`test_package/test_polkit.c`，链接组件 `polkit::gobject`） | **通过**：`polkit-gobject-1 OK: identity=unix-user:root subject=system-bus-name::1.42` |
| W4 Pre-PR 审计 | 见 `reports/`（PR 阶段执行，P0/P1 清零） |

## 5. 已知限制

1. **不含 `polkit-agent-helper-1`**（setuid root 特权 helper）。实测证据：OHOS sysroot
   的 `shadow.h` **无 `getspnam` 声明**，`libc.so` **无 `getspnam` 符号**
   （`nm -D` 零命中；对照 `getpwnam` 存在），即 musl libc **完全不提供 shadow 口令 API**；
   `pam` 路径所需的 libpam 在 OHOS 亦不存在。首轮构建即在
   `polkitagenthelper-shadow.c:100` 报 `int → struct spwd *` 隐式声明错误。
   故 libs-only 包只交付库，helper 留给上游 full 构建。
2. **运行期授权链需环境具备 D-Bus 系统总线 + polkitd + agent helper**（本仓库 `dbus`
   包只含客户端库 `libdbus-1`，无 `dbus-daemon`；polkitd 亦未适配）——本包交付的是
   **构建期依赖**（头/库/.pc 齐备，下游代理可编译链接）。
3. agent 库的文本监听器构造函数 `polkit_agent_text_listener_new()` 走 `GInitable`，
   需打开控制终端（`ctermid()`+`fopen("/dev/tty")`），CI 无 tty 必然失败；消费者测试
   改以类型系统 + `g_object_new()` 覆盖（等价证明库可加载/类已注册）。
4. 产物未 strip，调试字符串内含构建目录绝对路径。

## 6. 目录说明

```
124.1/
├── conanfile.py            # Conan 配方（CI 输入）
├── conandata.yml           # 源码地址 + sha256 + 补丁声明（CI 输入）
├── patches/                # 2 个补丁（CI 输入）
│   ├── polkitagent-libs-only.patch
│   └── mocklibc-ohos-fgetgrent-fgetpwent.patch
├── test_package/           # Conan L1 消费者测试（CI 输入）
│   ├── conanfile.py            # CMakeDeps 双组件构建 + 实跑两个用例
│   ├── CMakeLists.txt          # polkit::gobject / polkit::agent 两个消费者目标
│   ├── test_polkit.c           # gobject 组件回归用例
│   ├── test_polkit_agent.c     # 鸿蒙消费者用例（agent 库）
│   └── MANIFEST.yml            # 测试台账
├── manifest.yaml           # 编译元数据
├── notes.md                # 适配笔记（派生理由/补丁/shadow 缺口证据/踩坑）
└── reports/                # W3 本地 CI 日志、W4 审计结果、PR 正文
```
