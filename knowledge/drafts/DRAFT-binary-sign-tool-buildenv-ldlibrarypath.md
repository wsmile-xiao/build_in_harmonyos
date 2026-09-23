# DRAFT：binary-sign-tool 在 conan buildenv 下需剔除 LD_LIBRARY_PATH

> 状态：DRAFT（建议并入 E077 或晋升新条目）｜作者：B4Q2｜日期：2026-09-09
> 触发实例：cliquer/1.21（PR #9035，conan-verify G2 实撞 + 环境对照实验）

## 问题

cliquer/1.21 的 `package()` 内对产出的 `libcliquer.so` / `bin/cl` 做 HarmonyOS ELF 自签，
conan create 在 G2 的 package 阶段失败：

```
Error relocating /data/service/hnp/bin/binary-sign-tool: _ZNSt3__h15basic_streambuf...
Error relocating /data/service/hnp/bin/binary-sign-tool: _ZNSt3__h4coutE: symbol not found
ERROR: ... Error in package() method, line 84 ... ConanException: Error 127 while executing
```

同一配方在交互 shell 手动签名成功；`env -u LD_LIBRARY_PATH` 后立即恢复——强迷惑性的
"验证器挂、手动过"形态。

## 根因

ohos-aarch64 profile 的 `[buildenv]`（为 OHOS SDK lld 的 libxml2.so.16 依赖而设）把
`/data/service/hnp/ohos-sdk.org/<sdk>/ohos/native/llvm/lib` 前置进 `LD_LIBRARY_PATH`。
`binary-sign-tool` 的 `NEEDED libc++.so` 指向 HarmonyOS 系统 libc++（符号带
`std::__h` 内联命名空间）；LD_LIBRARY_PATH 使加载器命中 SDK llvm/lib 的 libc++
（`std::__1` 命名空间，无 `__h` 符号）→ 成串重定位失败 → exit 127。

## 最小复现与对照

```
$ LD_LIBRARY_PATH=<sdk>/llvm/lib binary-sign-tool sign ...   # → 成串 Error relocating
$ env -u LD_LIBRARY_PATH binary-sign-tool sign ...           # → 正常（[Error] inFile is not a elf file 属正常业务报错）
$ readelf -d binary-sign-tool                                 # NEEDED: libc.so, libc++.so
```

## 方案（env-unset-library-path）

配方内全部签名/objcopy 调用统一：

```
env -u LD_LIBRARY_PATH {llvm-objcopy} --remove-section .codesign "{f}"   # 先剥旧段
env -u LD_LIBRARY_PATH {binary-sign-tool} sign -inFile "{f}" -outFile "{f}" -selfSign 1
```

并保持 E077 的既有结论：签名是链接后、不再改文件内容的最后一步。

## 反例与禁止

- 禁止在 conan 环境内裸调用 `binary-sign-tool`：buildenv 注入不受配方控制，
  真机/CI 均为确定性失败。
- 修法必须写进配方本体（不要只改外层调用环境——CI 里没有"外层"）。

## 查重

- E077：覆盖签名顺序/剥 .codesign 段/内容哈希失效，**未覆盖** buildenv LD_LIBRARY_PATH
  劫持 libc++ 的失败面（grep 0 命中），本条为其补充；
- E524：讲依赖注入私有 prefix 防 SYS_PREFIX 污染——同为"环境变量注入击穿构建"家族，
  但对象与修法不同。

## 验证证据

- 失败日志：cliquer verify2 的 reports/conan-create.log（成串 relocating + Error 127）；
- 对照实验：干净环境与 `env -u` 后签名成功，产物可执行（explore5.log）；
- 修复后：cliquer conan-verify G2 PASS（verify3.log）→ finish W3 通过。
