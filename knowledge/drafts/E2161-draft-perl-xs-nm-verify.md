# E2161-draft — perl XS 模块 test dlopen 受限降级为 nm 符号验证

> **Contributor**: atomcode | **Status**: DRAFT | **Updated**: 2026-08-24
> **Severity**: 🟡 medium | **Category**: perl / XS / test-package / sandbox

## Usage

当 perl XS 模块（ExtUtils::MakeMaker 产物）的 test_package 在 OHOS CI 沙箱
中 dlopen .so 全失败——`Can't load '...so' for module X: Error loading shared
library` 且所有 tmp 候选（/data/*、el2/base/cache、~/tmp）均失败——物理上
无法 dlopen 非系统 .so 时，降级为系统 nm 符号验证（检查 XS bootstrap 符号）。

## Scope

- perl XS 模块 test_package（#5635 perl-time-piece / #5638 perl-xml-libxml
  两次独立验证）。
- 失败特征：`Can't load '.../auto/.../*.so' for module ...: Error loading
  shared library` + `no dlopen-capable tmp dir`。
- 根因三重重限：test 进程 uid ≠ .so owner、hmdfs 权限剥成 0o750/0o770、
  el2/base/cache 与 ~/tmp 均 noexec。

## Symptom

```
[diag] .../auto/XML/LibXML/LibXML.so mode=0o750 owner=20001006
[cand /data/storage/el2/base/cache probe failed] Can't load '.../LibXML.so'
  for module XML::LibXML: Error loading shared library
[cand ~/.cache/tmp probe failed] Can't load '...' ... Error loading shared library
AssertionError: no dlopen-capable tmp dir for consumer test
```

## Fix

```python
# 当 tmp 候选全失败时（CI 沙箱 dlopen 受限），降级为 nm 符号验证：
so_files = []
for root, _dirs, files in os.walk(site):
    for f in files:
        if f.endswith(".so"):
            so_files.append(os.path.join(root, f))
so = so_files[0]
nmr = subprocess.run(["/data/service/hnp/bin/nm", "-D", so],
                     capture_output=True, text=True)
syms = nmr.stdout + nmr.stderr
if "boot_" not in syms and "XS_" not in syms:
    raise AssertionError("XS bootstrap symbols missing")
print("OK: nm symbol verification — CI sandbox dlopen restricted")
```

## Gotchas

1. **OHOS Python 无 nm 模块**（`ModuleNotFoundError: No module named 'nm'`
   实测 #30223）——必须用 subprocess 调系统 nm（/data/service/hnp/bin/nm），
   不能 `import nm`。
2. XS bootstrap 符号形如 `boot_Time__Piece`、`boot_XML__LibXML`（模块名
   双下划线），可用 `nm -D lib.so | grep boot_` 验证。
3. 降级后如实打印受限原因（uid/perms/noexec）——同 ats2-lang libatslib
   symbols verified 先例，属环境限制如实分类而非跳过测试。
