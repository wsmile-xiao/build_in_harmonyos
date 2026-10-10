# DRAFT-tshark-4.6.7-ohos-cmake-unix-not-win32：CMake if(UNIX) 在 OHOS 为 false（uname=HarmonyOS），POSIX 源被静默丢弃

> Status: **Draft**（待审核 promote）| severity: `P1` | category: `platform` | Updated: 2026-09-28
> 对应: `knowledge/drafts/DRAFT-tshark-4.6.7-ohos-cmake-unix-not-win32.kv`

---

**匹配关键词**：if(UNIX), CMake, OHOS, HarmonyOS, POSIX, undefined reference, capture

## 错误签名（error_signature）

```text
undefined reference to .pcap
```

## 错误摘录（error_excerpt）

```text
tshark 4.6.7: capture 库 CMakeLists.txt if(UNIX) 分支在 OHOS（uname=HarmonyOS）下不生效，POSIX capture 源被丢弃（补丁 0001-capture-CMakeLists.txt.patch: if(UNIX) -> if(NOT WIN32)）
```

## 根因（root_cause）

OHOS 的 uname 返回 HarmonyOS，CMake 判定 UNIX=false，CMakeLists.txt 中 if(UNIX) 分支的 POSIX 源码被静默丢弃——configure 期无报错，仅链接/运行期 undefined reference 或功能缺失。tshark 4.6.7 实测：capture 库 POSIX capture 源被丢弃；4.4.16 归档曾因 CMake 平台问题 failed。

## 推荐方案（rec_approach: `平台判定条件 if(UNIX) 改为 if(NOT WIN32)（OHOS 满足 POSIX 语义）；CMake 项目适配前预扫 if(UNIX)/if(APPLE)/CMAKE_SYSTEM_NAME 分支逻辑并逐项对照 OHOS 环境核验。`）

---

*本文件为人工创建草稿（tshark 4.6.7 OHOS PC 适配实测经验）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
