# mda-lv2 1.2.12：LV2 宿主契约违反导致插件加载段错误（草稿）

- **软件**：mda-lv2 1.2.12（https://gitlab.com/drobilla/mda-lv2），结论适用于一切 lvz 包装的 LV2 插件
- **构建系统**：meson（上游），插件本体纯 C++（cpp_std=c++11）
- **平台**：HarmonyOS PC / aarch64，clang 15.0.4，本机原生构建
- **状态**：DRAFT

## 现象

test_package 探针 dlopen 插件成功、`lv2_descriptor()` 取描述符成功、URI 打印正常，
随后 instantiate() 直接段错误：

```
URI=http://drobilla.net/plugins/mda/TestTone
Signal 11 (core dumped)          # EXIT=139
```

## 根因

1. **features 传了裸 NULL**：LV2 规范要求宿主传"NULL 结尾的 feature 数组"，
   空集合也必须是 `{NULL}`（长度 1）。mda-lv2 的 lvz 包装层
   （`lvz/wrapper.cpp:100`）无防御地遍历：
   ```cpp
   for (int i = 0; features[i]; ++i) {
   ```
   features==NULL 时取 features[0] 即解引用 NULL → SIGSEGV。
2. **控制端口漏连接**：`lvz_run()` 逐个解引用 `control_buffers[i][0]`，
   run() 前未把全部控制端口 connect_port 到有效 float 缓冲同样 Signal 11。

真实复现（OHOS aarch64 本机，同一 TestTone.so）：
- `tnull <bundle>`（features=NULL）→ 打印 URI 后 Signal 11，EXIT=139
- `tload <bundle>`（`{NULL}` 数组 + 8 控制/2 进/2 出全连接）→
  instantiate + run(480) + cleanup 全生命周期 OK

合规宿主（JALV/Carla）按规范传数组不受影响；此坑只影响手写加载代码、
test_package 探针和 CI 集成测试——且崩溃栈落在插件 .so 内，极易被误诊为
"该 LV2 插件在 OHOS 上无法运行"。

## 处置

- instantiate 恒传 NULL 结尾数组：`const LV2_Feature* feats[1] = { NULL };`
- run() 前全端口 connect_port（端口数上界取 bundle 内 TTL 声明，mda-lv2
  最大 27 = JX10；atom/event 槽位传普通 float 缓冲无害——lvz 只存不读）
- 探针可自 typedef 最小 LV2_Descriptor/LV2_Feature 复刻，不依赖 lv2 包

## 验证

- 双探针对拍：NULL → 139；{NULL} → OK（见上）
- conan create（ohos-aarch64）test_package 以合规方式加载全部 36 插件，
  dlopen + instantiate + run + cleanup 全过

## 复用价值

任何在 OHOS 上为 LV2 插件（.lv2 bundle）写加载/集成测试的任务都会命中：
"插件 dlopen 成功但 instantiate/run 段错误" ≠ 插件坏了，先检查宿主侧两条
契约（features 数组 NULL 结尾、控制端口全连接）再下结论。判据是崩溃点若在
`lvz_instantiate`/`lvz_run` 的 features/端口遍历处，就是宿主契约问题，
改调用方一行即可，不要去改插件源码。
