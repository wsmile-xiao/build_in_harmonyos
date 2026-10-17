**DRAFT-rcheevos-12.2.1-float-to-unsigned-arch-ub — 浮点→无符号直接转型的架构分歧 UB（aarch64 fcvtzu 饱和 vs MSVC/x86 补码模式）与 musl c89 下 LFS *64 宏别名的声明缺失**

触发：rcheevos 12.2.1 上游测试套件在 OHOS aarch64 真机首跑 5/2712 失败（全部浮点转无符号类）+ 构建期 hash.c 的 fseeko64/ftello64 隐式声明错误。根因双重：①`(unsigned)f32` 负值是 UB，aarch64 合法饱和为 0 而 MSVC/x86 参考产出测试编码的补码模式；②musl 将 *64 LFS 名定义为无条件宏别名但 c89 严格模式隐藏 POSIX 声明。最小修复：转型经 int64_t 中转（源码一行）+ `-D_DEFAULT_SOURCE`（Makefile 一行）。修复后上游 2712/2712 全绿、消费者 8/8。

**身份与当前结论**

| 字段 | 内容 |
|---|---|
| 草稿 ID | `DRAFT-rcheevos-12.2.1-float-to-unsigned-arch-ub` |
| 配套结构化文件 | `knowledge/drafts/DRAFT-rcheevos-12.2.1-float-to-unsigned-arch-ub.kv` |
| 当前状态 | 已有验证证据待审（真机 target-executed） |
| 建议去向 | 新增模式（跨架构 UB + musl 特性宏两机制） |
| 实际贡献者 | atomcode-executor（任务执行） |
| 来源任务/PR | ohpcd contrib-10027；PR 创建后回填 |
| 提取方式 | 新适配过程提炼 |
| 本次交付 PR | 未创建（创建后回填） |
| 包及配方版本 | rcheevos / 12.2.1 |
| 上游版本与源码 | v12.2.1；https://github.com/RetroAchievements/rcheevos/archive/refs/tags/v12.2.1.tar.gz；sha256 14b3fd7d0b0b0cc33cb8ae446b357bb42bd40f9069f9af165f692aef6ff4fb22 |
| 知识来源提交 | （PR 分支提交后回填） |
| 被验证提交 | （PR 分支提交后回填；影子 CI 指纹一致） |
| 最后更新 | 2026-09-20 |

**1. 触发条件与可辨认现象**

| 条件 | 本次实际值 | 为什么影响结论 |
|---|---|---|
| 目标系统、架构 | HarmonyOS PC，aarch64，真机原生 | UB 的实际表现取决于目标架构指令（fcvtzu） |
| 编译器 | clang 15.0.4（aarch64-unknown-linux-ohos，musl libc） | c89 严格 + musl 特性宏共同触发构建期问题 |
| 构建 | 上游 test/Makefile：`-Wall -Werror -Wextra -pedantic -std=c89 -m64`（ARCH=x64 覆盖） | -Werror 把隐式声明变为硬错误 |
| 依赖 | 无 | 单因归因可信 |

首次失败原文（构建期，EVID-01）：

```text
../src/rhash/hash.c:188:3: error: implicit declaration of function 'fseeko' [-Werror,-Wimplicit-function-declaration]
  fseeko64((FILE*)file_handle, offset, origin);
sysroot/usr/include/stdio.h:213:18: note: expanded from macro 'fseeko64'
#define fseeko64 fseeko
```

补 0001 后测试运行期失败（EVID-02，5/2712，代表性两条）：

```text
* test_value/test_typed_value_convert(RC_VALUE_TYPE_FLOAT, 0, -1.0, RC_VALUE_TYPE_UNSIGNED, 0xFFFFFFFF, 0.0)
  Expected: value->value.u32 == u32   Found: 0 == -1
* test_value/test_evaluate_value("v5900_0xh0000*-1.0_0xh0001*-100.0", 4100)
  Expected: ret == expected_value   Found: 5900 == 4100
```

建议错误签名（与 KV 一致）：`Found:[[:space:]]+0 == -1$|Found:[[:space:]]+5900 == 4100|implicit declaration of function .fseeko.`
签名验证：失败样本命中（上述两段真实输出）；修复后样本（EVID-03 2712/2712 全绿日志）不命中。

**2. 根因与排除项**

机制一（运行期 UB）：`src/rcheevos/value.c:495` `value->value.u32 = (unsigned)value->value.f32;`——C11 6.3.1.4：负浮点转无符号为 UB。MSVC/x86 走 64 位转换路径得补码模式（测试编码的期望），aarch64 `fcvtzu` 饱和负值到 0。机制二（构建期）：musl `stdio.h` 无条件 `#define fseeko64 fseeko`，但 `fseeko` 声明在严格 c89（无 `_DEFAULT_SOURCE`/`_POSIX_C_SOURCE`）下不可见 → 宏展开后隐式声明。

| 可能原因 | 检查与证据 | 结论 |
|---|---|---|
| 测试本身写错 | 期望值与上游参考实现（MSVC CI）一致，x86 语义可复算 | 已排除 |
| -m64 导致（ARCH=x64 覆盖） | 失败值 0/-3/5900 与 -m64 无关，且 2707 项通过 | 已排除 |
| 编译器 bug | (unsigned)(-1.0f) 单独探针即得 0，符合 fcvtzu 文档语义 | 已排除（合法实现分歧） |

**3. 最小修复与选择条件**

1. `patches/0002-src-value-c-float-to-unsigned-via-int64.patch`：`(unsigned)(int64_t)f32`——经有符号 64 位中转在所有架构复现 MSVC/x86 语义（负值补码、[INT_MAX,2^31) 正值亦正确），不改行为契约。
2. `patches/0001-test-Makefile-default-source-for-musl-fseeko-decl.patch`：CFLAGS 追加 `-D_DEFAULT_SOURCE` 暴露 fseeko/ftello 声明（Makefile 一行，不动源码）。
3. 复用前核对：其他含 `(unsigned)float`/`(uint32_t)float` 直接转型的代码（同型检查 `grep -rn "unsigned)[a-z_]*\.f32"`）；其他 LFS `*64` 调用（ftello64/fseeko64/fopen64 等）在 musl 上均无独立符号，必须依赖特性宏或改用 POSIX 名。

```sh
# 真机复现与验证（多步）
conan create archives/r/rcheevos/12.2.1 -pr:h <ohos-aarch64> --build=missing
# 或直接： make -C test ARCH=x64 CC=<clang> runtests
```

上面的命令适用于：OHOS aarch64 原生环境。回退方案：未验证其他替代（如手写位级转换）；无需。

**4. 验证矩阵与证据绑定**

| 证据 ID | 类型 | 环境/输入 | 命令/入口 | 实际结果 | 日志 |
|---|---|---|---|---|---|
| EVID-01 | target-executed | 未打补丁构建 | make runtests | 编译失败：fseeko/ftello 隐式声明（-Werror） | job conan-create.log（第 1 轮） |
| EVID-02 | target-executed | 仅补 0001 | make runtests | **2707/2712**，5 项浮点转无符号失败（原文见上） | job conan-create.log（第 2 轮） |
| EVID-03 | target-executed | 补 0001+0002 | make runtests | **2712/2712 passed in 1 seconds** | job conan-create.log（终轮） |
| EVID-04 | target-executed | 打包后消费者 | conan create test 阶段 | ctest 1/1；消费者 8/8（激活/触发事件/排行榜/错误串/负例） | job conan-create.log（终轮） |
| EVID-05 | target-executed | 触发器状态机探针 | 设备侧 probe（内部 API） | 0,0,1 → state 5=TRIGGERED；后续帧返回 INACTIVE 保持 TRIGGERED（与上游 test_evaluate_trigger_triggered 注释一致） | job probe 输出 |

**测试统计**

| 层 | 单位 | 库存 | 通过 | 失败 | 跳过 | 未执行 | 依据 |
|---|---|---:|---:|---:|---:|---:|---|
| 上游（make runtests） | 断言 | 2712 | 2712 | 0 | 0 | 0 | EVID-03 框架输出 run_count |
| test_package 消费者 | CHECK | 8 | 8 | 0 | 0 | 0 | EVID-04 |
| 探针/负例实验 | 实验 | 3 | 3 | 0 | 0 | 0 | EVID-01/02/05 |

**5. 适用边界与禁止做法**

| 可复用前提 | 已验证 | 未验证/不适用 |
|---|---|---|
| C/C++ 含 float→unsigned 直接转型且参考语义来自 x86/MSVC | rcheevos 12.2.1 @ aarch64 | double→uint64 极值区间；x86 目标本身 |
| musl + 严格 c89 + LFS *64 调用 | OHOS clang 15 | glibc（*64 为真实符号）；宽松 -std=gnu*（默认暴露声明） |

| 错误做法 | 为什么不成立 | 后果 |
|---|---|---|
| 改测试期望迎合 aarch64 饱和值（forbid_1） | 上游测试编码参考实现契约 | 跨架构数据不一致 |
| 给源码加 __OHOS__ 宏分支绕开 | 平台宏补丁属仓库禁止模式（R8），且 UB 修复本就应跨架构统一 | 维护负担+评审拒绝 |

**6. 与已有知识的关系**

| 条目 | 已有内容 | 本次增量 | 建议 |
|---|---|---|---|
| E388 | （数值/转型类既有条目） | float→unsigned 的 fcvtzu/cvttss2si 指令级分歧与 int64 中转修法（若 E388 主题不同则为本条新增主体） | 对照后定 |
| DRAFT-E999-ohos-musl-long-double-double-alias | musl long double=double 别名 | 同族新例：musl LFS *64 宏别名 + 特性宏隐藏声明（构建期侧） | 补充 |
| musl-compat.md | musl 兼容清单 | 追加 fseeko64/ftello64 案例引用 | 补充 |

检索（2026-09-20，远端 main）：`float.*unsigned|fcvtzu|饱和|fseeko64|_DEFAULT_SOURCE` 于 knowledge/graph 与 knowledge/drafts，未见覆盖条目。

**7. 来源索引与提交自检**

| 材料 | 路径 | 版本角色 |
|---|---|---|
| 上游源码 | rcheevos v12.2.1 tarball | dc6153…同前（被适配对象） |
| 修复 | patches/0001、0002 | PR 分支提交后回填 |
| 证据报告 | archives/r/rcheevos/12.2.1/reports/knowledge-evidence.md | 同 PR |
| 原始日志 | 真机 job device-b/rcheevos-kb-20260920/conan-create.log（三轮） | 2026-09-20 |

- [x] ID/文件名/doc_file 一致；KV 单行字段与本文一致。
- [x] 引用路径在提交内；测试统计与正文一致（2712 上游 / 8 消费者）。
- [x] 关键结论均有 target-executed 证据；未验证边界已标注。
- [ ] PR 编号回填（提交前阶段注明）。

最终处理建议：可作为候选提交。剩余动作：影子 CI 后提交 PR 并回填编号。
