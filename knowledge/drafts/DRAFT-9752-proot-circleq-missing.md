# DRAFT-9752-proot-circleq-missing — OHOS/musl 系 <sys/queue.h> 缺少 CIRCLEQ 家族

> 任务 #9752（proot 5.4.0 OHOS arm64 适配）实测；draft（未提交评审）。

## 现象

proot 的 `src/path/binding.h` 使用 `CIRCLEQ_ENTRY`/`CIRCLEQ_HEAD` 定义绑定链表。
在 OHOS（musl 系、FreeBSD 衍生 `<sys/queue.h>`）上编译出现 12 处链式错误：

```
./path/binding.h:40:3: error: type name requires a specifier or qualifier
                CIRCLEQ_ENTRY(binding) pending;
                ^
./path/binding.h:46:41: error: expected function body after function declarator
typedef CIRCLEQ_HEAD(bindings, binding) Bindings;
```

根因：宏未被展开 —— OHOS 的 `<sys/queue.h>` 不含 CIRCLEQ 家族（`grep -c CIRCLEQ` = 0），
而同文件的 SLIST/STAILQ/LIST/TAILQ 均在。背景：FreeBSD 2018 年已删除 CIRCLEQ（很少使用），
OpenBSD/musl 同样不提供；glibc 仍提供，因此该问题只在 musl/OHOS 系（及 FreeBSD 新版本）复现。

## 证据

- OHOS 头文件实测：`sysroot/usr/include/sys/queue.h` 行数 880，`CIRCLEQ` 出现 0 次。
- 上游编译日志：见触发任务工作区 `proot-build.log`（12 处同族错误）。
- 修复后：`make -C src proot` rc=0；conan create / conan-verify G0–G4 / 本地 CI 门禁全绿；
  test_package 16/16（平台边界除外，与本题无关）。
- 他系参照：Alpine Linux 的 proot 包引入 `bsd-compat-headers`（提供完整 BSD 头含 CIRCLEQ），
  佐证"该缺失是 musl 系共性，不是 OHOS 独有"。

## 方案

`#ifndef CIRCLEQ_HEAD` 特性守卫下补标准宏族（自指针哨兵语义，与 glibc/旧 FreeBSD 一致），
放在第一个用到该宏的头文件里（proot 为 `src/path/binding.h`）。纯特性检测：

- 无平台宏（R8/PF5 干净）；
- glibc/Linux 构建走系统头，零影响；
- 同样适用于其它 musl 平台，天然可跨库复用。

## 边界（查重口径，2026-10-12 实查）

- **E091**（musl 系 `sockaddr_storage` 重定义）：结构体"重复定义"方向，本条是"宏家族缺失"方向，互补不重叠。
- **E194**（OHOS SDK 缺 `bits/alltypes.h` 等核心 musl 头，禁手写/复制）：本条不属于 libc ABI/类型缺口，
  补的是纯容器宏（不涉及 ABI 布局、不覆盖系统头），不落入 E194 禁区。
- **DRAFT-uapi-copy-guard-name-collision-predefine-package-guard**（UAPI 头守卫不同源导致枚举/结构体重定义）：
  同样是"重定义"类，与"缺失"方向不同。
- **DRAFT-9752 查重**：`grep -ril CIRCLEQ knowledge/` 零命中；engine 查询 `sys/queue.h CIRCLEQ missing musl`
  未命中 CIRCLEQ 条目（最近条目为 E194 的 musl 头不完整，方向不同）。

## draft-review 预审结果（2026-10-12 实跑）

```
python3 scripts/ohc-run.py draft-review DRAFT-9752-proot-circleq-missing --json --top 10
→ verdict: create
→ 最高相似 E032 0.110 / E093 0.110（signature_overlap=0.00, keyword_jaccard=0.00；
   仅 category_overlap 0.60 + phase 1.00 驱动）
→ E203 0.100、E196/E192/E313 0.09、E194 0.08、E091 0.07
```

初版签名含通用片段（implicit declaration of function 等）致最高相似 0.35（E093，伪相似）；
收紧为 CIRCLEQ 专有 token（CIRCLEQ_ENTRY / CIRCLEQ_HEAD / CIRCLEQ_REMOVE 等）后，
全部 signature/keyword 重叠归零，最高相似 0.11 → create。
E093（musl 缺 getpass）、E032（_BSD_SOURCE 头暴露）等均与本条无主题重叠。

## 触发实例（可复现）

- 仓库：`archives/p/proot/5.4.0/`
- 补丁：`patches/0002-src-path-binding.h.patch`（+101 行，全为宏定义，无平台宏）
- 复现命令：`grep -rn CIRCLEQ_ <src>/` + 对 OHOS sysroot 直接编译含 `CIRCLEQ_ENTRY` 的最小程序
