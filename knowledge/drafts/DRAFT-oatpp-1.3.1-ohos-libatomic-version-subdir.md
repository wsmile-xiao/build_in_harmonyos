# DRAFT — OHOS aarch64：libatomic 缺失 + CMake 版本子目录安装布局（oatpp 1.3.1）

**来源事件:** oatpp 1.3.1 适配（执行端 pc3-17，2026-09-02）
**状态:** 草稿（待 promote 审核）
**对应 .kv:** `DRAFT-oatpp-1.3.1-ohos-libatomic-version-subdir.kv`

## 问题

在 OHOS PC (aarch64, musl) 上交叉编译 oatpp 1.3.1 时依次遇到：

1. `ld.lld: error: unable to find library -latomic`——链接 `test/oatppAllTests` 阶段失败。
   OHOS musl sysroot 不提供 `libatomic.a`；oatpp 上游 `OATPP_LINK_ATOMIC` 默认 ON
   （CMakeLists.txt:21），会自动链接 libatomic。
2. 修复后 conan create 的 test_package 阶段：`Library 'oatpp' not found in package`
   随后 `fatal error: 'oatpp/web/server/HttpRouter.hpp' file not found`——因为 oatpp
   上游 `cmake/module-install.cmake` 把产物安装到**版本子目录**：
   `${libdir}/oatpp-1.3.0/liboatpp.a`、`${includedir}/oatpp-1.3.0/oatpp/...`，
   而 conanfile 的 `package_info()` 未声明这些子目录，CMakeDeps 按默认
   `lib/`、`include/` 查找必然落空。

## 根因

- OHOS 基于 musl libc，`libatomic` 未随 sysroot 提供；aarch64 的原子操作由 clang
  内建指令（LDADD/LDCLR 等）实现，**无需** libatomic 库。
- oatpp 采用多模块/版本化安装布局（module-install.cmake），与 Conan CMakeDeps
  的默认单目录假设不一致。

## 方案（已验证）

1. **上游选项优先，不改源码**：
   - `OATPP_LINK_ATOMIC=OFF` → 关闭 libatomic 链接（aarch64 clang 内建原子指令）。
   - `OATPP_COMPAT_BUILD_NO_SET_AFFINITY=ON` → 关闭 musl 缺失的
     `pthread_setaffinity_np`（上游 CMakeLists.txt:44/86 自带兼容开关）。
   - `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` → 兼容 CMake 4.x 对
     `cmake_minimum_required(<3.5)` 的拒绝（与 E103/E187 知识一致）。
2. **conanfile `package_info()` 显式声明版本子目录**：
   ```python
   self.cpp_info.libdirs = ["lib/oatpp-1.3.0"]
   self.cpp_info.includedirs = ["include/oatpp-1.3.0/oatpp"]
   self.cpp_info.libs = ["oatpp"]
   ```

## 验证

- 手动编译：`cmake .. -DBUILD_SHARED_LIBS=OFF -DOATPP_LINK_ATOMIC=OFF
  -DOATPP_COMPAT_BUILD_NO_SET_AFFINITY=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5 && make -j4`
  → oatpp/oatpp-test/oatppAllTests 全部链接成功。
- 上游测试：52 个独立用例实际运行全部通过（全量通过率 52/53=98.1%，1 个长迭代用例
  因单次执行预算中断，非失败）。
- 鸿蒙专项 HTTP 回环测试（test_package/test_oatpp.cpp）→ `OHOS_TEST_PASS`（exit 0，
  status=200，body 校验一致），conan create 内 ctest 1/1 Passed。
- conan-verify：G0-G4 + L2/L4/L5 全过。

## 适用边界

- 适用：OHOS aarch64 (musl) 交叉编译、上游默认链接 libatomic 的库；安装产物带
  版本/模块子目录的 CMake 库的 Conan 配方。
- 不适用：x86_64 OHOS（libatomic 可能需要）；上游无对应开关且无法关闭特性时
  需按 E211 走源码补丁方案。

## 查重差异

- libatomic 缺失：知识图谱 E260/E381/E452 不相关，index.tsv 无 atomic 命中 → **未命中**。
- 版本子目录安装：E217 覆盖"头文件装到 include/<PROJECT_NAME>"的 find 问题，
  但未覆盖 lib 子目录与 package_info libdirs 联动 → **部分覆盖、有新增差异**。
- affinity（pthread_setaffinity_np）：E094/E147/E211 已录根因（musl 缺失），
  但方案均为源码补丁/替换；本条目补充"优先查上游 compat 开关"路径 → 差异已并入本条。
