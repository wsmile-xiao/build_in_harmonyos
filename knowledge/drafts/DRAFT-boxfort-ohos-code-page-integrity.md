# DRAFT-boxfort-ohos-code-page-integrity：DRAFT-boxfort-ohos-code-page-integrity

> Status: **Draft**（待审核 promote）| severity: `3` | category: `platform|kernel|security|memory` | Updated: ?
> 对应: `knowledge/drafts/DRAFT-boxfort-ohos-code-page-integrity.kv`

---

## 触发面

- trigger_tool: `clang|any JIT/trampoline/sandbox library`
- phase: `runtime`

**匹配关键词**：mprotect, PROT_EXEC, SIGSEGV, /proc/self/mem, EPERM, MAP_FIXED, code page, trampoline, sandbox, patch_main, WIFSTOPPED, EPROTO

## 错误签名（error_signature）

```text
bxf_run.*-71|EPROTO.*wait_stop|WIFSTOPPED|Protocol error.*sandbox| mprotect.*EINVAL.*text|execve.*worker.*exit
```

## 根因（root_cause）

OHOS 内核对用户态可执行映射实施代码页完整性保护 (XPM), 实测 (HUAWEI MateBook Pro, OHOS 6.1.1, clang 15.0.4) 四条自改代码路径全部被封死: 1) mprotect(text_page, PROT_READ|PROT_WRITE|PROT_EXEC) -> EINVAL(22) 直接拒绝; 2) mprotect(text_page, PROT_READ|PROT_WRITE) -> 系统调用层放行但进程随即被内核 SIGSEGV 击杀; 3) 通过 /proc/self/mem pwrite 代码页 -> EPERM(13); 4) mmap(MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED) 覆盖已执行代码页 -> 进程被内核 SIGSEGV 击杀。 因此任何"先获得可写代码页再写跳板"的策略均不可行, 且无 /proc/self/mem 逃逸通道。

## 影响范围（affected_scope）

自修改代码类机制: boxfort patch_main 重执行跳板、运行时代码 patch、文本页内联 hook、依赖改写 main 的沙箱握手; 纯 JIT/闭包 (libffi) 见 E045, 本条补足"文件映射代码页"边界

## 推荐方案（rec_approach: `ohos-conditional-direct-run`）


## 验证方式（verification_cmd）

```text
对自身函数所在页: mprotect(RWX) 期望 EINVAL; mprotect(RW) 期望进程被杀; /proc/self/mem pwrite 期望 EPERM; boxfort 适配后 meson test 4/4 PASS (native) + conan create + test_package 12 断言 PASS (boxfort/0.1.2, feat/boxfort-0.1.2)
```

## 补充关键词

代码页, 自修改代码, XPM, W^X, mprotect, SIGSEGV, EPERM, MAP_FIXED, trampoline, self-exec, boxfort, sandbox, patch_main, text page

---

*本文件由 `knowledge/drafts/DRAFT-boxfort-ohos-code-page-integrity.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
