# Dear ImGui 1.92 headless 消费者：字体图集必须预构建，系统库需 --as-needed

> 状态：本地路径 B 草稿，需人工审核后才可提升为正式知识条目。

## 现象

imgui 生态库（implot/implot3d/ImGuizmo 等）的 `test_package` 在设备上以 headless 方式
（不初始化任何平台后端）运行 `ImGui::NewFrame()` 时：

1. 先打印一行空的 `[imgui-error] (current settings: Assert=1, Log=1, Tooltip=1)`，
   紧接着 `Signal 11 (core dumped)`，PASS/FAIL 断言一行都未输出。
2. 若消费者链接了 imgui 传递的 `ace_ndk.z/EGL/GLESv3` 系统库，运行时还可能报
   `Error loading shared library libc++.so: (needed by /system/lib64/libace_ndk.z.so)`
   或 `Error relocating /system/lib64/libsecurity_component_sdk.z.so: _ZNSt3__h... symbol not found`。

## 根因

- imgui 1.92 起字形按需烘焙（RendererHasTextures=false 的遗留路径需显式构建图集）。
  无后端消费者不构建图集就 NewFrame，首次取字形时解引用空烘焙数据段错误。
- imgui 的 `package_info()` 把 `ace_ndk.z/EGL/GLESv3` 声明为 system_libs 以支持其
  OHOS 后端；消费者可执行文件默认保留这些 DT_NEEDED，即使一个符号都没引用，
  加载器随即拉入应用级 Ace/NAPI 运行时链，其 libc++ inline namespace（__h）与
  hnp 工具链的 libc++（__1）冲突。

## 诊断证据（implot 0.8 实测）

- `ImGui::CreateContext(); io.DisplaySize=...; ImGui::NewFrame();` → 打印错误行后 SIGSEGV。
- 加 `io.ConfigErrorRecoveryEnableAssert=false` 后仍在同一点崩溃，与日志路径无关。
- `io.Fonts->Build()` + `GetTexDataAsAlpha8()` 后同一程序全链路成功：NewFrame →
  BeginPlot → PlotLine → EndPlot → Render，产出 vtx=516 idx=852。
- 链接命令去掉 `--as-needed` 时测试二进制运行报 `libace_ndk.z.so` 的 libc++ 加载错误。

## 推荐方案

```cpp
ImGuiIO& io = ImGui::GetIO();
io.DisplaySize = ImVec2(800, 600);
io.DeltaTime = 1.0f / 60.0f;
if (!io.Fonts->Build()) { /* FAIL */ }
unsigned char* px; int w, h;
io.Fonts->GetTexDataAsAlpha8(&px, &w, &h);   // 遗留图集构建入口
ImGui::NewFrame();
ImGui::Begin("win", ...);                    // 在窗口内绘图才有顶点输出
ImPlot::BeginPlot("probe"); ... EndPlot();
ImGui::End(); ImGui::Render();
assert(GetDrawData()->TotalVtxCount > 0);
```

```cmake
target_link_options(consumer_exe PRIVATE "LINKER:--as-needed")
```

## 禁止策略

- 不要为绕过崩溃伪造后端、stub ace_ndk 或跳过图集构建。
- 不要用 LD_PRELOAD 换系统 libc++，会污染全进程符号解析。

## 适用边界

- 适用于 imgui ≥1.92 的无后端消费者测试（conan test_package、CI smoke）。
- 需要真实 OHOS 后端的应用内集成不适用，应初始化 imgui_impl_ohos 后再 NewFrame。
- `--as-needed` 仅丢弃未被引用的系统库；若消费者真用 OHOS 后端绘制，则必须保留
  系统库链，改走完整后端路径。

## 与现有知识库的关系

- E464（mygui headless dummy 资源）、E471（gtk 无显示服务器分类）都是“显示上下文缺失”
  主题；本条针对 imgui 1.92 字形烘焙架构变化 + OHOS 系统库传播，查重未命中。
