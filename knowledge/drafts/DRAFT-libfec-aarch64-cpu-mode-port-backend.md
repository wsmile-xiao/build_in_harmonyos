# E-DRAFT: aarch64 缺失 CPU 模式探测后端（undefined symbol: Cpu_mode）

- **触发实例**：libfec 1.0 适配（2026-09-18，任务 libfec-1.0-r01-pc3-10）
- **错误签名**：`ld.lld: error: undefined symbol: Cpu_mode` / `undefined symbol: find_cpu_mode`（链接 vtest27 与 libfec.a）
- **类别**：aarch64, portability, autotools
- **严重度**：2（链接期确定性失败）

## 症状

```text
ld.lld: error: undefined symbol: Cpu_mode
>>> referenced by vtest27.c:38
ld.lld: error: undefined symbol: find_cpu_mode
>>> referenced by viterbi27.c (create_viterbi27) in archive libfec.a
```

## 根因

configure.in 的 `case $target_cpu` 只为 i386/powerpc/x86_64 设置 MLIBS（对应各平台
`cpu_mode_*.o` 探测实现），aarch64 落入 `*)` 空分支。但库内 viterbi 系列与所有
测试程序无条件调用 `find_cpu_mode()` 并引用全局 `Cpu_mode`/`Cpu_modes`——
aarch64 链接任一测试或库时就地崩溃。

## 解决方案

新增 `cpu_mode_arm64.c`（镜像上游 `cpu_mode_x86_64.c`：`Cpu_modes` 名称表 +
`enum cpu_mode Cpu_mode` + `find_cpu_mode()` 恒置 `Cpu_mode = PORT`），并在
configure.in 增加：

```m4
aarch64*|arm64*)
	MLIBS="cpu_mode_arm64.o"
	;;
```

aarch64（OHOS PC arm64）无 MMX/SSE 汇编实现，Portable C 后端即正确语义。

## 适用边界 / 反例

- 适用于上游仅配 x86/PPC 探测、代码无条件引用探测符号的库。
- 反例：若上游用 `#ifdef` 守护探测引用，则无需新增文件；禁止空宏/stub 伪装（R8）。

## 验证

```text
make test  →  8/8 上游用例通过（含 vtest27/vtest29/vtest39/vtest615）
nm libfec.a | grep find_cpu_mode  →  符号存在
```