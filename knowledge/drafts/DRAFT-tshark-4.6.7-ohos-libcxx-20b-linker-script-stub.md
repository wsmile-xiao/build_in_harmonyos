# DRAFT-tshark-4.6.7-ohos-libcxx-20b-linker-script-stub：OHOS SDK libc++.so 为 20B linker-script 桩，C++ 目标 undefined _Znwm/_Zdl

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `platform` | Updated: 2026-09-28
> 对应: `knowledge/drafts/DRAFT-tshark-4.6.7-ohos-libcxx-20b-linker-script-stub.kv`

---

**匹配关键词**：libc++.so, libc++_shared.so, linker script, 20 byte, _Znwm, _Zdl, OHOS, C++

## 错误签名（error_signature）

```text
undefined (reference|symbol).*_Znwm|undefined (reference|symbol).*_Zdl
```

## 错误摘录（error_excerpt）

```text
tshark 4.6.7: libwireshark.so undefined _Znwm/_Zdl（CMake/ccache 链接丢失 libc++_shared.so；SDK libc++.so 为 20B linker-script 桩）
```

## 根因（root_cause）

OHOS SDK 的 libc++.so 是 20 字节 linker-script 桩（INPUT(-lc++_shared)），非真实实现。裸 clang++ 会自动链接 libc++_shared.so，但 CMake/ccache 链接行不会自动带上，C++ 目标出现 undefined _Znwm/_Zdl（operator new/delete）。

## 推荐方案（rec_approach: `链接行显式加全路径 $OHOS_SDK/llvm/lib/aarch64-linux-ohos/libc++_shared.so（conan 配方：extra_exelinkflags + extra_sharedlinkflags）；先验证运行时可解析（实测：链接它的 trivial 程序无 LD_LIBRARY_PATH 可运行，用于 configure 探测程序也安全）。`）

---

*本文件为人工创建草稿（tshark 4.6.7 OHOS PC 适配实测经验）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
