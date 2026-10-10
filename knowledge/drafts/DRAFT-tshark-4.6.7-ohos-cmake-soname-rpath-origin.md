# DRAFT-tshark-4.6.7-ohos-cmake-soname-rpath-origin：交叉工具链 SONAME flag 探测为空，DT_NEEDED 指向构建树路径，包运行时无法解析自身库

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `platform` | Updated: 2026-09-28
> 对应: `knowledge/drafts/DRAFT-tshark-4.6.7-ohos-cmake-soname-rpath-origin.kv`

---

**匹配关键词**：SONAME, CMAKE_SHARED_LIBRARY_SONAME, RPATH, $ORIGIN, DT_NEEDED, symbol not found, OHOS, CMake

## 错误签名（error_signature）

```text
symbol not found|No such file or directory.*run/.*\.so
```

## 错误摘录（error_excerpt）

```text
tshark 4.6.7 L1: 安装后 'wtap_strerror: symbol not found'（内部 .so 无 SONAME，DT_NEEDED 指向构建树 run/ 路径；tshark 无 RPATH）
```

## 根因（root_cause）

OHOS clang/lld 交叉工具链使 CMake 的 CMAKE_SHARED_LIBRARY_SONAME_*_FLAG 探测为空，内部共享库无 SONAME，可执行文件 DT_NEEDED 记录构建树绝对路径（run/libwiretap.so）而非 SONAME；同时上游按 CMAKE_SYSTEM_NAME（Linux/SunOS/FreeBSD 等）门控 $ORIGIN install RPATH 的项目在 OHOS 全部不匹配，可执行文件最终无 RPATH → 安装后包运行时无法解析自身库（'symbol not found'）。

## 推荐方案（rec_approach: `配方强制注入 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG / CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG = '-Wl,-soname,'（尾逗号必须：CMake 以无分隔符方式拼接 flag 与 soname，缺逗号 lld 拒收融合 token）+ ENABLE_RPATH_ORIGIN=ON（或等效 $ORIGIN RPATH），使包自包含可重定位。`）

---

*本文件为人工创建草稿（tshark 4.6.7 OHOS PC 适配实测经验）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
