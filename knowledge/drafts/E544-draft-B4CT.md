# E544 — 2005 年代 config.sub 连 aarch64 现代三元组也不识别：原生构建只传 --build 不传 --host

> 触发实例: cityhash 1.1.1 适配（任务 #6466，PR #9054，OHOS aarch64 原生构建 / Conan 2.29.1 / clang 15），2026-09-09。

## 错误特征

conan create 的 configure 阶段报（两者常先后出现）：

```text
checking build system type... aarch64-unknown-linux-gnu      ← 显式 --build 后直接指定
checking host system type... Invalid configuration `aarch64-unknown-linux-ohos': machine `aarch64-unknown-linux' not recognized
configure: error: /bin/sh ./config.sub aarch64-unknown-linux-ohos failed
```

若不传任何参数，则是另一形态：

```text
configure: error: cannot guess build type; you must specify one
```

## 触发条件

- 构建系统: autotools（随包发布的 config.guess/config.sub 为 2005-2011 年版本）
- 阶段: configure（canonical 三元组解析）
- 平台: OHOS aarch64（UNAME_SYSTEM=HarmonyOS、UNAME_MACHINE=aarch64）

## 根因分析

两层问题叠加：

1. **config.guess 层**（相关经验 E160）：若 configure 必须从 uname 猜 build 类型，老 config.guess 不认识 `UNAME_SYSTEM=HarmonyOS`/`HongMeng`，会报 `cannot guess build type`；本实例显式传 `--build`，不依赖该猜测路径。
2. **config.sub 层**（本条核心）：`aarch64` 这个 CPU 名 2012 年前后才进入 config.sub 词汇表。2005 年代的 config.sub 连 `aarch64-unknown-linux-gnu` 都判 `machine aarch64-unknown-linux not recognized`——所以给 `--host=aarch64-unknown-linux-ohos` 必然失败，这不是"ohos 后缀不认识"（E072/E122），而是 **CPU 名整体不在列表**。

## 解决方案

### 推荐方案（OHOS 原生构建，设备即目标机）
1. configure 只传 `--build=aarch64-unknown-linux-gnu`（config.sub 认识），**不传 --host**——host 缺省等于 build，绕开 config.sub 对 host 三元组的校验；
2. 编译器由 `CC=`/`CXX=` 显式给出（Conan AutotoolsToolchain 环境）；
3. 若另一条构建路径不显式传 `--build`，再按 E160 为 config.guess 增加 HarmonyOS 分支。

cityhash 1.1.1 实测：E011 补丁 + 仅 `--build` 后 configure 完整通过，构建、上游测试、消费者测试全部成功；本 PR 未应用 E160 config.guess 补丁。

### 禁止做法
- ❌ 传 `--host=aarch64-unknown-linux-ohos`——老 config.sub 直接 `Invalid configuration` 终止。
- ❌ 试图 sed 让 config.sub 接受 ohos——CPU 名都不认识，补 OS 后缀没用。

## 验证

```bash
# 诊断：老 config.sub 对现代 CPU 名的接受度
./config.sub aarch64-unknown-linux-gnu     # 报 Invalid configuration 即中招
./config.guess                              # 报 cannot guess build type 同源
# 修复后：conan create 全流程通过
conan create . -pr:h=<profile> --build=missing
```

## 关联条目
- 相似: E007（cannot guess build type → patch-autotools-script 的通用形态）
- 相关: E160（config.guess 的 HarmonyOS 分支补丁——不显式传 `--build` 时的相关方案；本 PR 未应用）
- 相关: E122/E072（config.sub 对 ohos 后缀的校验问题——发生在较新 config.sub 上，CPU 名已识别，与本条 CPU 层问题不同）
