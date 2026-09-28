# DRAFT-kio-kwallet-6.28.0-cmake-version-soversion-symlink-e018

## 现象
- conan create 链接阶段失败：`cmake -E cmake_symlink_library` → `Permission denied`。
- 直接在 conan 的 python 里 `os.symlink()` → `Operation not permitted`（EPERM）。
- 交互 bash 中 `ln -s` 正常 → 排除文件系统权限/挂载问题。
- 陷阱：仅 `set_target_properties(... VERSION "")` 置空仍拼出 `libKF6Wallet.so.`
  （尾点号文件），继续为它创建版本链 symlink，再次触发同一 EPERM。

## 根因（OHOS 沙箱域隔离，E018）
- 沙箱按**进程域**授予 symlink(2)：conan python 进程树及其 fork/exec 出的
  make/cmake 子进程全部继承一个对 symlink 一律 EPERM 的域。
- 该域同时没有 exec 转移（链式 exec 无法越界）：可 exec /system/bin（toybox）、
  /data/service/hnp/*、.pi/agent/bin/*，不可 exec /usr/bin、$HOME 下新建脚本。
- 只有把 VERSION/SOVERSION 目标属性**整行删除**才能让 cmake 完全不生成版本链。

## 解法（copy-instead-of-link）
1. 补丁删除 `set_target_properties(<tgt> PROPERTIES VERSION ... SOVERSION ...)`。
2. configure() 注入 `CMAKE_SHARED_LINKER_FLAGS=-Wl,-soname,lib<NAME>.so.<SOVER>`
   → 主 .so 保留上游 DT_SONAME（`readelf -d` 验证）。
3. package() 在签名前 `cp lib<NAME>.so lib<NAME>.so.<SOVER>`，两份都走 OHOS
   .codesign 签名；消费者运行时收集 glob `lib*.so*` 同时覆盖。

## 验证
- kio-kwallet/6.28.0：conan create 全绿，双文件签名，test_package 1/1。

## 关联
- E002（/tmp 只读/TMPDIR）；kwallet/6.18.0 基线同方案。
