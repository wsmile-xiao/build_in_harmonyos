# DRAFT-kea-hook-ping-check-3.0.3: OHOS /storage 沙箱拒绝符号链接——meson 版本化 soname 的物化修法

- **条目 ID**: `DRAFT-kea-hook-ping-check-3.0.3-ohos-storage-symlink-denial-soname`
- **严重度**: 2（🟡 中等）
- **类别**: meson, symlink, packaging, runtime, testing, portability, ohos, filesystem
- **触发工具/阶段**: meson | conan | ldso — testing / packaging / runtime
- **来源**: kea-hook-ping-check 3.0.3 适配（feat/kea-hook-ping-check-3.0.3，OHOS PC aarch64）
- **路径**: Path B（知识库扩展）
- **与已有条目关系**: `similar_to: E492`（见文末「与 E492 的关系」）

## 症状

kea-hook-ping-check 3.0.3（Meson 构建）真机第五轮：meson setup/compile 全程
通过，但 `meson test` 两个套件 0.05s 内双双 FAIL（exit status 127），stderr 刷屏：

```
Error loading shared library libkea-dhcpsrv.so.131: (needed by .../dhcp-ping-check-tests)
Error relocating .../dhcp-ping-check-tests: _ZNK3isc9Exception4whatEv: symbol not found
```

同一构建树的 test_package 阶段随后也死在同一个名字上：

```
dlopen(.../p/lib/kea/hooks/libdhcp_ping_check.so) failed:
Error loading shared library libkea-dhcpsrv.so.131
```

但构建树里 `libkea-dhcpsrv.so.131.0.0`（实文件）明明存在且完整。

## 根因

1. **OHOS /storage 沙箱在文件系统层拒绝创建符号链接**：`ln -s` 直接
   Permission denied，新构建树 `find -type l` 计数为 0。
2. **meson 的版本化共享库发布方式**：`shared_library(... version: '131.0.0')`
   链接产物是实文件 `libkea-X.so.131.0.0`，soname 名 `libkea-X.so.131` 只以
   **符号链接**指向它。符号链接建不出来 → soname 名文件在 OHOS 上根本
   不存在。
3. **加载器按 NEEDED 名查找**：测试二进制与插件闭包的 DT_NEEDED 记录的是
   soname（`libkea-dhcpsrv.so.131`），加载器找文件必然落空——先报"库加载
   失败"（空原因），再级联成"符号重定位失败"（其实不是符号问题）。
4. **为什么家族模板 kea-hook-limits 没踩中**：它的 build() 不跑 meson test
   （从不执行测试二进制），package() 里又有 islink 分支的复制兜底——本配方
   一跑上游测试就暴露。

## 最小复现

```meson
# 任意上游共享库，version 语法即触发
shared_library('dhcp_ping_check', sources, version: '1.0.0')
```

OHOS 真机上构建 + 执行任何依赖该库 NEEDED 闭包的二进制（`meson test` 或
dlopen）必现。`ln -s a b` 单独执行即可复现沙箱拒绝。

## 已试过的失败方案

1. 给构建目录换到 /tmp：/tmp 在 OHOS 上只读，更早失败。
2. `-Dc_link_args=-Wl,--no-versioned...` / 改版本号：soname 是上游语义，
   不能动。
3. 只修测试二进制的 rpath 指到实文件名：测试二进制几十个、插件本体还引用
   soname，改不干净。
4. package() 里 os.symlink 失败后什么都不做：包内 soname 缺失，dlopen 同样
   失败（本轮 test_package 初版即此）。

## 解决方案

1. **build() 物化 soname**：compile 后 `_materialize_sonames()` 遍历构建树
   库目录，对每个 `libkea-X.so.N.M.K` 实文件以 `shutil.copyfile` 复制出
   soname 名 `libkea-X.so.N`；名字已存在（普通 Linux 宿主 meson 已建
   符号链接）则跳过——幂等，常规宿主上仍只有一个物理文件。
   - meson test 二进制（LD_LIBRARY_PATH 含全部构建目录）自动吃到副本；
   - package() 的遍历（`startswith("{lib}.so.")`）把 soname 名当普通文件
     复制进包 → 包内闭包完整。
2. **package() 空产物复核**：真机曾出现包内 soname 文件落盘 0 字节的瞬时
   异常（/storage 写回问题，一次性的，未能复现根因）。package() 收尾对每个
   Kea 库做 `getsize()==0` 复核，空文件从构建树重拷并打 WARNING 日志——
   自愈 + 可观测。
3. **test_package 闭包兜底**：`test_ohos_runtime` 把包内 40 个库（20 个
   soname 名 + 20 个全版本名）逐个 `dlopen(RTLD_NOW)`，任何漏网的空文件/
   缺失名都会在验证层被拦下。

## 验证

第六轮真机 conan create：`_materialize_sonames()` 后 meson test 两套件全绿
（Ok: 2 / Fail: 0；dhcp-ping-check-tests 90 例 = PASSED 42 + SKIPPED 48
[Root 组在无 CAP_NET_RAW 沙箱下自动跳过，0 FAILED]，libloadtests 4/4）。
package() 复核逻辑 + test_package 3/3 通过（hook 加载、平台 ABI、40/40
闭包 dlopen），conan-verify 全绿。

## 与 E492 的关系

E492（zix 0.8.1，2026-08-25 入库）已覆盖主干：「meson 构建出版本化实库，但
OHOS 构建/安装树不暴露 SONAME 别名 → 物化别名，符号链接可用时优先相对符号
链接，被拒绝时复制实 ELF 回退」。本条目与它的增量：

1. **根因层次钉深一层**：E492 停在「别名没有暴露」；本条目实测钉到文件系统
   层——OHOS /storage 沙箱对 `ln -s` 直接 EPERM，新构建树 `find -type l`
   计数为 0。这解释了为什么「优先相对符号链接」在 OHOS 上必然走 copyfile
   回退，也给出可复现的最小检查（`ln -s a b` 一条命令即可验证沙箱行为）。
2. **0 字节落盘瞬时异常与自愈**：真机曾出现 package 产物 soname 落盘为
   0 字节（mode 0640 = 全新 umask 创建，与 copyfile 的 0770 可区分）的
   一次性异常，E492 未覆盖；本条目给出 package() 收尾 `getsize()==0` 复核
   自愈 + WARNING 可观测的处置。
3. **消费方闭包兜底**：test_package 把包内 40 个库（20 个 soname 名 + 20 个
   全版本名）逐个 `dlopen(RTLD_NOW)`——任何漏网的缺失名/空文件都会在验证层
   被拦下，而非等消费者运行时才炸。
4. **家族配方为何不踩的判读**：不跑 meson test 且 package() 有 islink 分支
   兜底的配方（家族模板 kea-hook-limits）不会命中；只要一执行测试二进制即
   暴露——这是排查时判断「哪个家族配方会踩」的直接线索。
