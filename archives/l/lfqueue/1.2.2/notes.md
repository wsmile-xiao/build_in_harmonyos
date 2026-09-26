# lfqueue 1.2.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 (OHOS / aarch64-linux-ohos)
- 状态: published

## 编译步骤

1. `git worktree add -b feat/lfqueue-1.2.2 ...` 从 main 创建专用 worktree（R01，唯一匹配）
2. 官方源码下载: GitHub tag 1.2.2 归档（sha256 83b515da...224a9）
3. CMake 构建（上游 CMakeLists 声明 cmake_minimum_required(2.8)，CMake 4.x 需 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`）：
   ```bash
   CC=clang CFLAGS="-fPIC -O2 -std=c11" cmake .. -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   make
   ```
   产物: liblfqueue.a / liblfqueue.so / lfqueue-example
4. 上游测试: `ctest -N` 注册 1 项 lfqueue_test（lfqueue-example）
5. conan 配方: CMakeToolchain + BUILD_SHARED_LIBS 门控 + 补丁去除 install-time ldconfig（OHOS 无 ldconfig）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 配置失败: "Compatibility with CMake < 3.5 will be removed" | 上游 `cmake_minimum_required(2.8)` 过旧 | 配方 generate() 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | 上游 install(CODE ldconfig) 在 OHOS 失败 | OHOS 无 ldconfig | 补丁 0001 移除该行并让库目标遵循 BUILD_SHARED_LIBS；头文件装到普通 include/（上游装到 lfsaq/ 子目录） |
| 3 | 上游测试 lfqueue-example 多出多个场景（one_enq_and_multi_deq / one_enq_and_multi_deq_must）50/50 通过；multi-enq+single-deq 场景（one_deq_and_multi_enq / one_deq_must_and_multi_enq）5/5 运行挂起 | 上游 lock-free 竞态：`_single_dequeue` 立即 free(head)，与并发 `_enqueue` 的 `CAS(&tail->next)` 及 tail 推进竞争，可致 UAF/活锁 | 如实记录；消费者测试用 lfqueue_deq（非 single_deq）路径规避；症状非平台问题（单 enq 多 deq 全过证明队列核心可用） |

## 源码修改

- patches/0001-cmake-ohos-static-shared.patch: CMakeLists 库目标按 BUILD_SHARED_LIBS 建 static/shared；移除 install-time ldconfig；头文件装到 include/（而非 lfsaq/）

## 依赖版本

无外部依赖（纯 C11 + GCC/Clang __sync 内建）。

## 验证结果

```bash
# 上游自测（ctest lfqueue_test，见 MANIFEST.yml 注：multi-enq+single-deq 场景上游竞态挂起，已有证据）
ctest -N          # Test #1 lfqueue_test
./lfqueue-example # 单 enq+multi deq 场景 50/50 通过；multi-enq+single-deq 场景挂起（上游缺陷，见 notes 表#3）

# 消费者测试（test_package，conan create 内自动运行）
./test_lfqueue    # lfqueue consumer: enqueued 100000, sum OK, size=0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | - | CMake 型配方（BUILD_SHARED_LIBS 门控） |
| conandata.yml | - | 官方 tag 1.2.2 URL + sha256 |
| patches/0001-cmake-ohos-static-shared.patch | - | OHOS 构建/安装适配补丁 |
| test_package/test.c | - | 真实消费者测试（10 万项 enq/deq 校验） |

## 注意事项

- 上游锁自由队列存在 multi-enq+single-deq 竞态（`_single_dequeue` 立即 free 与 tail 推进竞争），文档建议单消费者用
  `lfqueue_single_deq`，但并发多生产者 + single_deq 仍可挂起；消费者测试采用 `lfqueue_deq` 路径规避。
- CMake 2.8 语法老，任何 CMake >= 4 环境都必须带 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
- R38: lfqueue 是纯库（无 bin 可执行），不产生 commands.json。
---

**编译结束**: 2026-09-24 21:01
**最终状态**: published
