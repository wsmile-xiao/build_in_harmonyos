# E401 — Libretro 核心 dlopen 消费者测试必须先注册 retro_set_environment 再 retro_init

## 错误特征

test_package 鸿蒙专项测试直接 dlopen libretro 核心（如 `mednafen_vb_libretro.so`）后调用
`retro_init()`，在 `retro_init` 处段错误：

```
RUN: ./test_beetle-vb-libretro-ohos '<core>.so'
Signal 11 (core dumped)
ERROR: ConanException: Error 139 while executing
```

首次运行（未注册 environ 回调）必然复现；同一核心在补上回调注册后通过。

## 触发条件

- 构建系统: 任意（libretro 核心为 dlopen 插件库，与构建系统无关）
- 阶段: test_package 消费者测试 / 前端集成运行时
- 前提: dlopen 核心后调用 `retro_init()` 前**未**调用 `retro_set_environment()`

## 根因分析

Libretro ABI 的固定契约：前端通过 `retro_set_environment(struct retro_environment_callback)`
注入 `environ_cb` 回调，`retro_init()` 内部直接解引用该回调
（`RETRO_ENVIRONMENT_SET_PERFORMANCE_LEVEL` / `GET_VARIABLE` / `GET_LOG_INTERFACE` 等）。
消费者测试若跳过注册动作，`environ_cb` 为 NULL → `retro_init` 处 SIGSEGV。

注意：知识引擎对 "Signal 11 / core dumped" 的 E338 命中仅为关键词重叠——E338 根因是
OHOS 的 `getpwuid` 返回 NULL 导致 homedir() 为 NULL，与 libretro 回调注册完全无关，
不能据此复用 E338 的 env 注入/源码守卫方案。

## 解决方案

### 推荐方案

在 test_package 消费者测试中，`dlopen` 后、`retro_init` 前调用 `retro_set_environment` 注册
最小 environ 回调（libretro 文档默认行为）：

```c
static bool test_ohos_environ(unsigned cmd, void *data) {
    (void)data;
    switch (cmd) {
        case 8:   /* RETRO_ENVIRONMENT_SET_PERFORMANCE_LEVEL */
        case 10:  /* RETRO_ENVIRONMENT_SET_PIXEL_FORMAT */
        case 16:  /* RETRO_ENVIRONMENT_SET_VARIABLES */
            return true;
        default:  /* GET_VARIABLE / GET_LOG_INTERFACE / GET_PERF_INTERFACE 等 */
            return false;
    }
}
/* 调用顺序 */
retro_set_environment(test_ohos_environ);
retro_init();
/* 断言: retro_api_version()==1; retro_get_system_info() 的 library_name /
 * valid_extensions; retro_get_system_av_info() 的 fps/sample_rate/geometry */
retro_deinit();
dlclose(handle);
```

### 禁止做法

- ❌ 直接 dlopen → `retro_init()`（不注册 environ 回调）
- ❌ 把 Signal 11 误判为平台限制或当前库代码缺陷而打补丁改核心源码
- ❌ 用 E338（passwd NULL）的方案处理本错误

## 验证

```bash
# 修复前（无 set_environment 前置）→ Signal 11, RC=139
clang test_ohos.c -o test_beetle-vb-libretro-ohos -ldl && ./test_beetle-vb-libretro-ohos '<core>.so'

# 修复后 → 完整生命周期通过
ohos lifecycle ok: fps=50.27 sample_rate=44100.00 geometry=384x224 extensions=vb|vboy|bin
# conan-verify G2 PASS (exit 0)
```

## 适用边界与反例

- 适用：所有 libretro 核心（beetle-* 系列、mupen64plus、snes9x、gambatte 等）的
  OHOS 消费者测试；模式可整体复用，仅改核心文件名与断言常量。
- 反例：普通共享库（无 `retro_*` 符号）不需要也不应调用 `retro_set_environment`；
  常规 dlopen + 调用导出 API 即可。
- 与 E442/E345（从宿主应用树剥离的 ELF 插件打包策略）方案不重叠。

## 关联条目

- 相关: E338（仅关键词重叠，根因不同）、E442、E345、E283、E392
- 前置: 后续 libretro 核心 OHOS 消费者测试
- 证据: archives/b/beetle-vb-libretro/1.2.8/test_package/test_ohos.c + reports/conan-create.log