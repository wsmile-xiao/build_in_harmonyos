# E430 — OHOS 内核 ppoll() 运行时返回 ENOMEM：需强制 pselect 路径

## 错误特征
- 运行使用 `ppoll()` 多路复用的 C/C++ 工具（如 ninja 子进程调度）时，日志无限循环刷：
  `ninja: ppoll: Out of memory`
- 对应 syscall 层面为 `ppoll() == -1, errno == ENOMEM`，进程不退出但任务永远无法完成。

## 触发条件
- 构建系统/工具：ninja（或任意调用 ppoll() 的守护进程/构建工具）
- 阶段：testing/runtime（子进程事件循环）
- 平台：HarmonyOS PC（OHOS aarch64，toybox/bionic poll 层限制）

## 根因分析
OHOS PC 内核的 `ppoll()` 在运行时返回 ENOMEM（toybox/bionic poll 限制），
并非资源真实耗尽，而是平台 poll 族系统调用语义缺陷。ninja 默认使用 ppoll()
做子进程多路复用，因此其上游测试套件（`./ninja_test`）会卡死在事件循环刷屏。
上游自身提供 `NINJA_FORCE_PSELECT=ON` 编译选项切换到 `pselect()` 路径，实测规避成功。

## 解决方案

### 推荐方案
构建时设置 `NINJA_FORCE_PSELECT=ON`（等价 pselect 开关）：
```bash
cmake -S . -B build -DBUILD_TESTING=ON -DNINJA_FORCE_PSELECT=ON -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++
cmake --build build --target ninja_test -j2
./build/ninja_test   # 411 tests ran, 无 ppoll ENOMEM 刷屏
```
Conan 配方中在 `generate()` 写入 `tc.variables["NINJA_FORCE_PSELECT"] = "ON"`。

### 禁止做法
- ❌ 修改上游事件循环改用自定义 poll 实现（改库行为，违反最小改动原则）
- ❌ 用超时观察/前台限时把刷屏误判为测试结论

## 验证
```bash
# 未强制 pselect：./ninja_test 刷 "ninja: ppoll: Out of memory" 无限循环（run1 日志）
# 设置 -DNINJA_FORCE_PSELECT=ON 后：411 tests / 407 passed / 4 failed，1.4s 跑完
# （ninja_test_run4.log 摘要见台账）
```

## 适用边界
- 适用：使用 ppoll() 的 C/C++ 构建工具/守护进程（OHOS aarch64）
- 反例：纯 Linux 环境 ppoll 正常，无需强制 pselect

## 查重差异
- exact_duplicate: false（全库 ppoll/pselect 0 命中）
- trigger_overlap: 低（E055 posix_spawn subprocess compat 是 fork/spawn 语义，非 poll 系统调用）
- combination_novelty: true —— "OHOS 内核 poll 族系统调用运行时失败 → 构建工具强制 pselect 开关" 为组合新知识

## 关联条目
- similar_to: E055（子进程系统调用 compat）
- caused_by: OHOS 内核 ppoll 实现
- prerequisite_of: ninja 上游测试子进程套件可运行
