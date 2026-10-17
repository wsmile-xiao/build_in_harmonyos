# blessed 0.1.81 鸿蒙适配笔记

## 环境信息
- 操作系统：HarmonyOS 6.0（aarch64）
- 构建系统：无（纯 JavaScript，npm 分发）
- Node.js 运行时：消费者需自备（>= 0.8.0）

## 依赖
- 无运行时依赖

## 构建步骤
1. 从 npm registry 下载 tarball
2. Conan 配方复制文件到 package/lib/node_modules/blessed
3. 通过 NODE_PATH 环境变量暴露给消费者

## 测试结果（全部通过 ✅）

### 上游冒烟测试

### 鸿蒙专属测试
PASS: Core API exports
PASS: Screen instance
PASS: Box instance
PASS: Content manipulation
PASS: Event system
PASS: List component
ALL_HARMONYOS_TESTS_PASSED


## 关键问题与解决方案

### 问题 1：NODE_PATH 环境变量为空
- **原因**：`self.run()` 默认使用 `conanbuild` 环境，不含 `runenv_info`
- **解决**：`self.run(cmd, env="conanrun")` 显式使用运行环境

### 问题 2：Node.js 崩溃（Signal 5 / core dumped）
- **现象**：`Check failed: 12 == (*__errno_location())`
- **原因**：OHOS 沙箱拦截 `mmap(PROT_EXEC)`，V8 初始化 JIT 内存失败
- **解决**：使用 `node --jitless <file>` 禁用 JIT

### 问题 3：conandata.yml 格式错误
- **现象**：`TypeError: argument after ** must be a mapping, not list`
- **原因**：`sources` 被写成 list（`- url:`），`get()` 需要 dict（`url:`）
- **解决**：改为 dict 格式

### 问题 4：Conan 2 中主配方 test() 不执行
- **原因**：`conan create` 只调用 `test_package` 的 `test()`
- **解决**：把上游测试合并进 `test_package/conanfile.py`

## 沙箱使用注意事项
- `node -e "..."` 内联执行必崩（立即编译触发 JIT）
- `node <文件.js>` 在顶层通道可运行，但需要 `--jitless`
- 任何 fork 出的子进程中的 Node 都会崩溃
- 推荐始终使用 `node --jitless <file>`

## 相关 PR
（待填写）