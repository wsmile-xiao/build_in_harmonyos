# E-OPENAL-ALEXT-PROTOTYPES（草稿）— OpenAL Soft 扩展函数原型守卫与 loopback 无头验证

配套条目：`knowledge/drafts/openal-1.24.1-alext-prototypes-loopback.kv`
实证包：`archives/o/openal/1.24.1`（OpenAL Soft 1.24.1，OHOS aarch64，clang 15/libc++ 15）

## 现象（error_signature）

```
test_openal.c:157:9: error: use of undeclared identifier 'ALC_FORMAT_CHANNELS_SOFT'
test_openal.c:171:14: warning: call to undeclared function 'alcLoopbackOpenDeviceSOFT';
                      ISO C99 and later do not support implicit function declarations
test_openal.c:171:12: error: incompatible integer to pointer conversion assigning to
                      'ALCdevice *' from 'int'
```

## 根因（root_cause）

`<AL/alc.h>` 只声明核心 ALC API。ALC_SOFT_loopback 的枚举宏在 `<AL/alext.h>` 无条件
`#define`，但扩展**函数原型**（alcLoopbackOpenDeviceSOFT / alcIsRenderFormatSupportedSOFT /
alcRenderSamplesSOFT）整段包在 `#ifdef AL_ALEXT_PROTOTYPES` 内（1.24.1 alext.h L311-315，
全文件共 10 处同型守卫）。只 include 不定义宏 → 枚举可用、函数退化为隐式声明（int 返回），
于是"undeclared identifier（枚举）"与"implicit function declaration + int→指针（函数）"
两类错误交替出现，看似头文件没装全，实为宏未定义。

## 推荐处置（rec_approach）

1. include `<AL/alext.h>` 前 `#define AL_ALEXT_PROTOTYPES 1`。
2. OHOS 无音频设备的功能验证走 loopback：`alcLoopbackOpenDeviceSOFT(NULL)` +
   `alcCreateContext(attrs: ALC_MONO_SOFT/ALC_SHORT_SOFT/8kHz)` + `alcRenderSamplesSOFT`。
3. 渲染断言用波形特征：0.5 FS 正弦渲染后 peak≈0.5×32767（实测 16383）；过零次数
   ≈2×频率×时长（正弦每周期升/降各过零一次；220 Hz×0.12 s≈52.8，实测 54）。
   只断言"非零"会放过静音/坏输出。
4. null 后端：`setenv("ALSOFT_DRIVERS","null",1)` 强制；`alGetString(AL_VERSION)` 返回
   `"1.1 ALSOFT <版本>"`，可直接断言被测版本号。

## 验证命令（verification_cmd）

```bash
printf '#define AL_ALEXT_PROTOTYPES 1\n#include <AL/alext.h>\nint main(void){return alcLoopbackOpenDeviceSOFT(0)!=0;}' \
  | clang -xc - -c -o /dev/null && echo ALEXT_OK
```

## 关联条目

- E092（CMAKE_SYSTEM_NAME=HarmonyOS 平台识别；CMake 打印 "System is unknown to cmake"
  属预期噪音，探测全部正常）
- 1.25.2 对照：`archives/o/openal-soft/1.25.2/notes.md`（1.25.2 全项目 C++20，在 OHOS
  libc++15 上需 9 个兼容补丁；1.24.x 仍为 C++17，零补丁）
