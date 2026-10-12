# E998 — 平台头探针假阳性让 x86 专属符号混入单产物插件库，导致整库 dlopen 失败

> 知识条目草稿：`knowledge/drafts/E998-draft-B183-pd-external-unresolved-symbol.kv`
> 来源：pd-zexy 2.4.4 在 OHOS aarch64 上的适配（样例库），状态：待主编审核

## 一句话

构建系统用「头文件存在」推断「接口存在」，在 musl 目标上得到假阳性 → x86 专属对象被编进
**同一个**共享库 → 未解析符号在链接期放行、在 `dlopen` 期爆炸 → **整库所有类一起不可用**。

## 现象（实测）

pd-zexy 2.4.4（89 个 `.c` 链成单一 `zexy.pd_linux`：350528 B，ELF shared object，aarch64）：

| 阶段 | 结果 |
|------|------|
| `make -j1 CC=<clang> PDINCLUDEDIR=<puredata>/include/pd` | **rc=0**（构建层面一次通过，无任何警告级阻断） |
| 上游回归套件 `make check` / `tests/testrunner.sh`（36 项） | **13 PASS / 19 FAIL / 4 XFAIL** |
| 宿主报错 | `error: ./zexy.pd_linux:Error relocating ./zexy.pd_linux: ioperm: symbol not found` |
| 同文件符号清点 | `nm -uD zexy.pd_linux \| grep -xE 'ioperm\|iopl\|inb\|outb'` → **1 行（ioperm）** |
| 加 `with-lpt=no` 后 | **32 PASS / 0 FAIL / 4 XFAIL**，同清点 → **0 行** |

注意「构建成功」与「可用」的巨大落差：编译、链接、install 全部成功，产物却是废的——
19 项测试失败的根因只有一个符号。

## 根因（三层）

**① 探针层：头存在 ≠ 接口存在。**
pd-lib-builder 用 `$(CPP)` 探 `<sys/io.h>`：OHOS sysroot **装了**该头（内核 uapi 侧），
但 musl **不提供** `ioperm` / `inb` / `outb` 一组并口系统调用。探针看到头就定义
`HAVE_SYS_IO_H`，进而把 `src/lpt.c`（x86 并口）编进来。zexy `Makefile` 的 `forLinux`
分支正是「检查 `sys/io.h` 是否存在」——这个判据在 glibc 上成立、在 musl + OHOS sysroot
上必然假阳性。

**② 传播层：共享对象的未定义符号在链接期是合法的。**
`-shared` 链接默认允许未定义符号留待运行时解析，因此 `make` 不会失败，`ld.lld` 不报错。
**「编译通过」对插件库不能作为验收判据。**

**③ 爆炸层：单产物库「一坏全坏」。**
宿主 `dlopen` 时按 RTLD 全量重定位，一个符号缺失即**整个** `zexy.pd_linux` 加载失败，
库里约 90 个类（含与并口毫无关系的 list/symbol/DSP 类）全部不可用 —— 单符号让
36 项回归挂掉 19 项（52%）。单产物插件架构（Pd 外部库、VST、内核模块风格）天然如此。

## 通用性 / 同类识别清单

- 构建系统用 `AC_CHECK_HEADERS` / `__has_include` / `$(CPP) -E` **按头判能力**，而目标
  libc（musl）缺对应符号 → 一律需复核符号层；
- 上游代码含平台专属子系统（并口/串口/GPIO/ioctl 直通/setup 级指令）且被条件编译门控；
- 产物是「一个 `.so` 装下全部功能」的插件式架构（失败面 = 库规模）；
- 同族：pd-lib-builder 构建的 Pd 外部库（zexy/iemlib/cyclone/iemnet/…）遇到同类子系统即复现。

## 处理方案

**推荐（优先找上游开关，不打补丁）**

```python
# archives/p/pd-zexy/2.4.4/conanfile.py
self.run('make -j1 CC="{}" PDINCLUDEDIR="{}" with-lpt=no'.format(cc, pd_include),
         cwd=self.source_folder)
```

`with-lpt=no` → 非 `with-lpt` 路径统一注入 `-DZ_WANT_LPT=0`，直接不编译该对象。
**先找开关**（`configure --help`、Makefile 变量、README），关闭单一子系统就能让全库恢复。

**回退（无开关时）**：补丁条件化该对象（`#if` 守卫或从 `class.sources` 摘除），
并在 PR 说明理由（R8 口径：平台宏默认禁止堆砌，须有实质逻辑）。

**禁止**
1. 以「编译/链接成功」判定适配完成 —— 必须做符号层检查或真实 `dlopen` 冒烟；
2. 用**绝对路径**把上游回归补丁喂给 `tests/testrunner.sh`（见下节，会导致假失败）；
3. 只跑抽样/单类测试 —— 单产物库抽样无意义，且空壳测试会被 L1e/R34 反向验证判负。

## 验证方法

```bash
# 1) 符号层归零（本类最直接的判据）
nm -uD <pkg>/lib/pd-externals/zexy.pd_linux | grep -xE 'ioperm|iopl|inb|outb|inb_p|outb_p' | wc -l   # 期望 0

# 2) 定位探针与开关
grep -nE 'sys/io\.h|HAVE_SYS_IO_H|Z_WANT_LPT|with-lpt' src/Makefile src/src/*.c

# 3) 端到端：test_package 内跑上游全套回归（本样例 36 项，断言 FAIL==0 且 TOTAL>=36）
conan create . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64> --build=missing --user=ohpcd --channel=stable
```

## 附：上游回归套件的正确跑法（本次踩到的第二个坑）

`tests/testrunner.sh` 的补丁参数必须是**相对路径**（等价上游 `make check` 从源码根跑
`find tests/*/ -name '*.pd'`）。用绝对路径时会假失败：

```
error: abs: can't load abstraction within itself   # tests/absgn~/abs.pd
```

原因：该补丁内的 `abs` 抽象名在绝对路径下被 pd 解析成补丁自身。实测同一份产物、
同一台机器：绝对路径 **FAIL=1 / PASS=31**，相对路径 **FAIL=0 / PASS=32** —— 纯路径形态
差异，与被测库无关。test_package 驱动脚本因此显式 `cd "$STAGE"` 后用相对路径收集补丁。

## 样例库与复用

| 项 | 位置 |
|----|------|
| 适配产物（样例库） | `archives/p/pd-zexy/2.4.4/conanfile.py`（`with-lpt=no` + 上游套件接入） |
| 消费者测试 | `archives/p/pd-zexy/2.4.4/test_package/{conanfile.py,run_upstream_suite.sh,MANIFEST.yml}` |
| 同族技能（A 类 PD 拓展） | `skills/pd-externals-ohos/`（配套 PR #14210，尚未合入 main；构建期无 cc/头集/符号作用域；与本条互补） |
| 检测规则 | 本条目 `prescan_pattern: sys/io\.h|ioperm|iopl|\boutb\b|\binb\b|Z_WANT_LPT|with-lpt`（promote 后由 PreScanner 自动派生 `PSCAN-KB-E998`） |

## 边界与未决

- 本条目只覆盖「产物整体不可加载」这一类；「根本构建不起来」（无 cc、头集缺失、
  musl 符号作用域）由同族条目覆盖（见 kv 内 `similar_to` 说明，待主编互链）。
- 未验证：其他 Pd 外部库是否同样带 x86 专属子系统（按需在后续适配中回填 `metrics_*`）。
- `ioperm` 一族在 aarch64 上即使有也语义不同：本类问题的正解是**不编译该对象**，
  而不是补 stub（stub 会改变上游语义且掩盖真实能力缺口）。
