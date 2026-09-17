# E429 — ArkTS/NAPI 像素缓冲集成契约：external ArrayBuffer 不可用于 createPixelMap；异步图像对象必须最后 release

> 草稿（draft）：与归档适配同一原子 PR（#10116，分支 `feat/curtain-0.3`）交付，待主编评审与编号。
> 贡献者：kasumizawa-miyuu <241250031@smail.nju.edu.cn>

## 错误特征

失败 1（内存语义，错误日志即刻可见）：

```
E C02B61/om.kasumizawamiyuu.curtainhost/PixelMapNapi: colors mismatch
（紧跟在 CurtainPage: setSource=true 1024x768 之后；PixelMap 始终为 null，幕布不显示）
```

失败 2（生命周期，崩溃日志）：

```
Reason:Signal:SIGSEGV(SEGV_MAPERR)@0x0000005bfbbe8500
Fault thread info:
#00 ... stub.an(BCStub_HandleLdobjbynameImm8Id16StwCopy+1572)
#01 at initAsync entry (entry/src/main/ets/pages/Curtain.ets:<await 之后的续体行>)
...
========SubmitterStacktrace========
#03 ... libimage_napi.z.so(OHOS::Media::PixelMapNapi::ReadPixelsToBuffer(napi_env__*, napi_callback_info__*) (.cfi)+1016)
#02 ... libace_napi.z.so(napi_queue_async_work_with_qos+44)
#01 ... NativeAsyncWork::QueueWithQos(...)
#00 ... libuv.so(uv_queue_work_with_qos_internal+448)
```

稳定签名（可在 hilog/faultlog 直接 grep）：

```
colors mismatch | PixelMapNapi | ReadPixelsToBuffer | SIGSEGV(SEGV_MAPERR)
```

## 触发条件

- 平台：HarmonyOS PC（HarmonyOS 6.1.0.117，API 23；开发机 SDK API 22）
- 技术栈：ArkUI（ArkTS）宿主 + NAPI 原生模块（C/C++）+ `@kit.ImageKit`
- 阶段：runtime（应用启动初始化图像管线）
- 场景：
  1. NAPI 侧把 native 像素缓冲以 **external ArrayBuffer**（零拷贝）返回给 ArkTS，再由 ArkTS 调
     `image.createPixelMap(buffer, {size, pixelFormat})`；
  2. ArkTS 侧对 `ImageSource`/`PixelMap` 的异步调用（`createPixelMap`/`getImageInfo`/`readPixelsToBuffer`）
     **在全部 await 完成之前**调用 `release()`。
- 实例：curtain 0.3 原生宿主（C 核心输出屏幕尺寸 RGBA，ArkTS 每帧/启动期建 PixelMap；实测
  `colors mismatch` 1 次、cppcrash 3 次：14:14:45 / 14:18:59 / 14:20:18）。

## 根因分析

### A. `image.createPixelMap` 不接受 NAPI external ArrayBuffer

- `napi_create_external_arraybuffer` 创建的外部缓冲，其内存所有权与释放时机由 NAPI（finalizer）管理，
  长度/内存语义是“外部资源”；
- ArkTS `image.createPixelMap(ArrayBuffer, options)` 期望的是**常规 ArkTS ArrayBuffer**，会按其
  `size.width*height*alpha` 校验并复制到 PixelMap 自己的内存；
- 传 external ArrayBuffer 实测直接报 `PixelMapNapi: colors mismatch`（或在个别时序下进程崩溃），
  PixelMap 创建失败，后续 `Image(pixelMap)` 无画面。
- 结论：NAPI 像素输出必须 `napi_create_arraybuffer` + `memcpy` 返回**拷贝**。零拷贝在此接口上不可用。

### B. 异步图像对象的 release 时机 = use-after-free

- `ImageSource.createPixelMap`、`PixelMap.getImageInfo`、`PixelMap.readPixelsToBuffer` 都是异步接口：
  NAPI 侧经 `napi_queue_async_work_with_qos` 把工作排到异步队列，完成后 resolve Promise；
- 若在 await 链全部完成前 `release()`（或让 C 侧释放对应缓冲），随后异步回调 resolve、
  ArkTS 续体恢复执行时访问的已是**已释放对象**；
- 崩溃特征具有强规律性：
  - 主线程崩溃点位于 `initAsync` 中 **await 之后的续体行**（`#01 at initAsync entry (...Curtain.ets:NN)`）；
  - 崩溃上报栈（Submitter）显示当时仍在排队的 `PixelMapNapi::ReadPixelsToBuffer`；
  - `Reason: Signal:SIGSEGV(SEGV_MAPERR)@0x...`（疑似 NULL/失效指针解引用）。
- 结论：release 必须**严格晚于所有 await**；中间任何提前释放都会在“看起来无关”的续体行崩溃。

## 解决方案

### 推荐方案（curtain 0.3 最终补丁已验证）

1. **NAPI 返回拷贝缓冲**（C++）：

```cpp
size_t length = (size_t)curtain_core_width(g_core) * (size_t)curtain_core_height(g_core) * 4;
void *data = nullptr;
napi_value value;
if (napi_create_arraybuffer(env, length, &data, &value) != napi_ok || data == nullptr) {
  napi_get_null(env, &value);
  return value;
}
memcpy(data, pixels, length);
return value;   // 禁止 napi_create_external_arraybuffer
```

2. **release 推迟到全部 await 之后**（ArkTS）：

```ts
const source = image.createImageSource(buffer);
const decoded = await source.createPixelMap({ desiredPixelFormat: image.PixelMapFormat.RGBA_8888 });
const info = await decoded.getImageInfo();
const rgba = new ArrayBuffer(info.size.width * info.size.height * 4);
await decoded.readPixelsToBuffer(rgba);
// ... setSource / getPixels / await image.createPixelMap(scaled, ...) 等全部异步完成后 ...
decoded.release();
source.release();
```

3. **多对象/循环场景**：把 `release()` 集中到最后一个 await 之后统一执行；不要在循环体内提前释放。
4. **验收口径**：
   - `hilog -x` 无 `PixelMapNapi: colors mismatch`，且 `pixelMap=true`；
   - `/data/log/faultlog/faultlogger/` 不再新增该应用 cppcrash；
   - `snapshot_display` 截图出现真实画面（像素内容正确）。

### 真实证据（curtain 0.3）

| 证据 | 内容 |
| --- | --- |
| hilog | `01-launch.log`：`CurtainPage: setSource=true 1024x768` 后紧跟 `PixelMapNapi: colors mismatch`（adapter 首版 external ArrayBuffer） |
| cppcrash ×3 | `/data/log/faultlog/faultlogger/cppcrash-com.kasumizawamiyuu.curtainhost-20020153-2026091514{1445,1859,2018}*.log`：SIGSEGV(SEGV_MAPERR)，栈含 `ReadPixelsToBuffer` 与 `initAsync` 续体 |
| 修复后 | `conan create` 全绿；真机 `pixelMap=true`、全屏遮罩/揭开/穿透/回盖/关闭/重启全部 PASS（test-report 第 4/6 节） |
| 提交 | 修复包含在 `d7103a553`（拷贝缓冲 + 延后 release）；后续 NAPI 加固 `e36b48dfa`（数组长度与空指针防护） |

### 禁止做法

- 不要再用 `napi_create_external_arraybuffer` 把像素缓冲交给 ArkTS image API（零拷贝在此不可行）。
- 不要在 image 异步调用完成前 `release()`（哪怕“这段代码看起来只是初始化”）。
- 不要把 `colors mismatch` 当成颜色格式配置错误（改 `desiredPixelFormat` 无效），根因在缓冲内存语义。

## 验证

```bash
# 运行日志（期望：无 colors mismatch，pixelMap=true）
hdc shell hilog -x | grep -E "PixelMapNapi|CurtainPage"

# 崩溃日志（期望：不再新增 curtainhost cppcrash）
hdc shell "ls -t /data/log/faultlog/faultlogger/ | grep curtainhost"

# 画面（期望：真实渲染内容而非空白）
hdc shell snapshot_display -f /data/local/tmp/shot.jpeg
```

## 关联条目

- 相关：E474（ArkUI 原生消费者验证契约——讲“怎么验收”，本条讲“运行时内存/生命周期契约”）；
  E462（用户态 SIGSEGV 调试——讲定位手段，本条给出具体崩溃签名与成因）；E321（OHOS 图形栈 API 面差异）。
- 差异（新增价值）：现有知识库（766 条索引 + 651 份草稿）中 `PixelMap`/`napi_` 相关检索无命中
  （`grep -rn "PixelMap" knowledge/` 为空）；本条首次沉淀“NAPI↔ArkTS 像素缓冲”两类契约与可复制的
  验收口径，适用于所有 ArkUI+NAPI 宿主应用。
