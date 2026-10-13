# DRAFT: test_package 静态 DT_NEEDED 检查把系统 libz.so 误判为未解析

> 实例：vigor 0.016（archives/v/vigor/0.016，PR #15200 / CI #80207）
> 关联知识：E541（OHOS 系统自带 libz.so，Conan 不得发布共享 libz.so）、
> E186（patchelf-fix-runpath 处理 libz.so 运行时缺库）、
> DRAFT-polkit-qt-1-0.201.1-ohos-sdk-layout-probe（同类"本地过、CI 挂"布局差异）

## 场景

依赖 tcl/tk 9 的 OHOS aarch64 Conan 配方，其 test_package 自己实现了静态
DT_NEEDED 解析断言（不依赖 readelf/objdump，用 Python 解析 ELF .dynamic 段，
逐个校验 NEEDED 库能否在 LD_LIBRARY_PATH + sys_paths 中找到文件）。

## 症状

- 构建成功，`vigor -e -r` 真实执行 rc=0（运行时加载器能找到所有 NEEDED 库）
- 但 `all DT_NEEDED libraries resolve` 断言失败：
  ```
  [FAIL] all DT_NEEDED libraries resolve  -- unresolved=['libz.so'] ...
  VIGOR TEST SUMMARY: 8 passed, 1 failed
  ERROR: vigor/0.016 (test package): Error in test() method
  [fail] vigor/0.016 — conan create failed
  ```
- 本机复现：用 CI 等价的 LD_LIBRARY_PATH + 本机 sysroot 路径跑 vigor_test.py
  是 9/9 通过；把硬编码的本机 sysroot 候选清空（模拟 CI worker 布局）即复现
  `unresolved=['libz.so']`（8 passed, 1 failed）——与 CI #80207 完全一致。

## 根因

1. tcl/tk 9.0.3.2 配方 `cpp_info.system_libs = ['dl', 'm', 'pthread', 'z']`，
   AutotoolsDeps 给下游链接注入 `-lz`，链接器把系统 libz.so 写进产物 DT_NEEDED
2. HarmonyOS 本身提供系统 libz.so（E541），运行时加载器在 worker/设备按系统
   默认路径即可解析——所以真实执行成功
3. test_package 的静态断言用 `os.path.isfile` 遍历 `LD_LIBRARY_PATH` +
   硬编码的 `sys_paths`（本机 dev 布局 `/storage/Users/currentUser/usr/local/
   sysroot/usr/lib/aarch64-linux-ohos` 等）；CI worker 是
   `/data/service/hnp/ohos-sdk.org/...` 布局，没有这些路径 → libz.so 被误判
   未解析
4. 本机恰好有该 sysroot 路径 → 本地 9/9 通过、CI 失败——典型的"本地过、
   CI 挂"环境布局差异

## 修复

test_package/vigor_test.py 的 DT_NEEDED 解析循环中，把 `libz.so` 与
`libc.so`/`libc.so.6` 同等视为 loader/system-resolved（E541 依据），直接跳过
静态路径校验，不要求它在 LD_LIBRARY_PATH 或 sys_paths 中可 isfile：

```python
for lib in needed:
    if lib in ("libc.so", "libc.so.6"):
        continue
    if lib == "libz.so":
        # OHOS system library (E541) ... loader-resolved on worker/device
        continue
    ...  # 其余 NEEDED（X11/tcl/tk 链）仍按静态路径严格校验
```

关键：只豁免系统库，**不删除/不注释整个断言**（R9：禁止伪造通过）——X11/tcl/tk
链的真实未解析缺库仍会被拦截。

## 验证

```bash
cd archives/v/vigor/0.016
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing 2>&1 | tail -3
# 期望: VIGOR TEST SUMMARY: 9 passed, 0 failed（exit 0）
```

模拟 CI worker 布局（去掉本机 sysroot 候选）跑 vigor_test.py 也应 9/9。

## 关联

- 与 DRAFT-polkit-qt-1-0.201.1-ohos-sdk-layout-probe 同类：本地 dev 布局与
  CI worker 布局不一致导致"本地过、CI 挂"，排查方向是环境布局而非编译/链接。
- 与 E541 直接相关：系统 libz.so 属平台提供，Conan 不发布共享 libz.so。
