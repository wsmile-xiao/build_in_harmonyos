# 无头 CI 下"核心功能需 GPU/GL context"的库如何写出真 test_package

> 草稿（DRAFT）。与同目录 `opencsg-1.8.2-ohos-headless-context-dependent-test-contract.kv` 成对。

## 问题

一些库的核心功能必须依赖运行时上下文：图形库需要真实 OpenGL/GLES context，音频库需要设备，
显示库需要窗口系统。CI worker **无头、无 GPU**，直接调用核心渲染/播放接口必然失败。

两种常见错误应对：

- **跳过测试** → 等于没有验证；
- **写空壳测试**（只 `printf`、不调用被测包 API）→ 违反 R34/L1d，且 CI 的 **L1e 破坏性反向验证**
  （移走产物后重跑测试）会识破。

## 可复用契约：无上下文断言 + 运行时加载器探针

把库的公开 API 分成两类，分别处理：

**(1) 无上下文部分 → 实质断言**
版本宏、核心对象构造/析构、setter/getter、内部状态机、全局选项、上下文键管理等。
这些调用被测包的**真实符号**，L1e 移走产物后会链接/运行失败，满足 R34。

**(2) 运行时加载器探针**
`dlopen` 该库在目标平台上真正依赖的运行时库，`dlsym` 解析配方补丁所依赖的入口符号。
既证明平台前提成立，又不创建上下文。

**(3) 需上下文的路径 → 如实延后**
在 `test_package/MANIFEST.yml` 与 `notes.md` 写明"需应用侧/真机真实 context"，
**不得**谎称已覆盖。

## 为什么这样能过门禁

| 门禁 | 要求 | 本契约如何满足 |
|------|------|----------------|
| R34 | 测试实质调用被测包 API | 无上下文断言全部链接并调用真实符号 |
| L1 | test_package 被真实执行 | 测试进程实际运行并输出断言结果 |
| L1e | 移走产物后测试必须失败 | 测试依赖被测包符号/头文件/库文件，破坏后链接或运行失败 |

## 抽查方法

```bash
# 测试二进制应对被测包有未定义符号依赖（证明不是空壳）
llvm-nm -D -u <test_binary> | grep <LibNamespace>
llvm-readelf -d <test_binary> | grep NEEDED
```

## 证据（opencsg 1.8.2，render() 需真实 GL context）

- 无上下文断言 9 项：版本宏、`Primitive` 构造析构 + `setOperation`/`setConvexity`/
  `setBoundingBox`、`setOption`/`getOption`、`setContext`/`getContext`。
- 运行时探针 2 项：dlopen `libGLv4.so` 解析 `glGetString`；dlopen `libEGL.so` 解析 `eglGetProcAddress`。
- 设备 shadow CI：`test_opencsg: PASS`、`L1_RESULT=pass`、
  `L1e: Negative test confirmed — test genuinely depends on opencsg`。
- 未覆盖（如实记录）：`render()` 的 Goldfeather/SCS + FBO/遮挡查询路径。
- 本地对测试二进制 `nm -D -u` 检查：13 个 OpenCSG 符号由 `libopencsg.so` 解析。

## 适用范围

图形渲染、音频、显示、输入，以及任何需要设备/服务才能工作的库。凡是"核心功能跑不起来"
但"库本身能装上"的场景，都可套用这套契约。
