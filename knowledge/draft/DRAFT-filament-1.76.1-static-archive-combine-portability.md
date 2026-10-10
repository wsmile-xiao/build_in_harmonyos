# DRAFT-filament-1.76.1-static-archive-combine-portability

> Contributor: ohos-farm | Status: Draft | Updated: 2026-09-17
> Source: filament 1.76.1 HarmonyOS PC 适配（PR #10480）
> 领域：portability|build-system|static-archive|conan

## 背景

Filament 1.76.1 的 `libs/filamat` 用上游 `build/linux/combine-static-libs.sh` 把 glslang、SPIRV-Tools、spirv-cross、zstd 等 9 个归档合并成 `libfilamat.a`。在 HarmonyOS PC（aarch64-linux-ohos）上该步骤先后以三种不同表象失败：`mv: bad '*.o'`、filamat POST_BUILD 中断、以及最隐蔽的 `ENAMETOOLONG`。

## 错误签名

```text
mv: bad '/storage/.../tmp/_libfilamat_combined/libSPIRV-Tools-opt/
         libSPIRV-Tools-opt_libSPIRV-Tools-opt_..._eliminate_dead_output_stores_pass.cpp.obj'
make[2]: *** [libs/filamat/CMakeFiles/filamat.dir/build.make:487: libs/filamat/libfilamat.a] Error 1
```

## 根因

见 `.kv` 的 root_cause：扩展名硬编码、cwd 依赖、暂存目录跨轮复用导致前缀叠加、以及 `object_files()` 不转发 `-delete` 造成的静默清理失效。

## 触发条件

构建脚本合并多份静态库；脚本硬编码 `*.o`；scratch 由输出名派生且只 `mkdir -p`；进程 cwd 可能在构建期变得不可读。

## 修复方案

见 `.kv` 的 solution：扩展名从归档内容推导、路径全绝对化、整轮清一次、参数转发。

## 验证

见 `.kv` 的 verification：T1/T2/T3 与判别组对照，成员集可复现且与旧脚本可区分。

## 适用与反例

适用：任何把多份静态库合并成单库的构建脚本。
反例：已用 `mktemp -d` 派生唯一暂存目录、且路径全绝对化的脚本不受影响。
