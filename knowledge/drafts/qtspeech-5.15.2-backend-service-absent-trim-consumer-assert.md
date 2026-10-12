# qtspeech-5.15.2-backend-service-absent-trim-consumer-assert（拟 E753）

> Contributor: j669539 / Status: **DRAFT** / Updated: 2026-10-07 / Source: PR !14839
> 拟提升编号：E753（最终由主编确认；与 E752 同批申报，取号经过见 .kv number_note）

## 症状

上游按平台特性探测组装插件的模块（qtspeech 5.15.2 实测：src/tts/configure.json 探测
speechdispatcher / flite / sapi / winrt / osx / ios / android 七类 TTS 引擎后端），
在 OHOS 上无 speech-dispatcher 守护进程、无 flite 合成器服务：

- src/plugins/tts 编译出**零插件**（本地原型实测 plugins/ 目录为空）
- libQt5TextToSpeech 本体完整（readelf -d NEEDED 仅 libQt5Core.so.5 + libc++_shared.so + libc.so）
- 上游 texttospeech 套件 5 个引擎依赖用例必然失败，全部携带文档化签名：

```
FAIL!: tst_QTextToSpeech::say_hello()
   QSYSTEM : No text-to-speech plug-ins were found.
```

危险的双重性：既不能把**真实缺陷**当环境限制豁免（漏放行），也不能把**文档化的无引擎
行为面**当缺陷强修（库本体没坏）。

## 根因

OHOS 平台服务缺位 ≠ 库缺陷。上游 configure.json 特性探测正确地裁剪了不可用的引擎插件，
库按上游文档定义的无引擎行为面工作（state()==BackendError、-guarded API、0.0 默认值、
空 voice 模型）。测试侧的真正问题是**划界**：哪些失败是环境使然、哪些是缺陷，以及
消费者拿到的库到底承诺了什么——后者上游测试根本没有覆盖（上游假设有引擎）。

与 E550 族（可选依赖静默降级：autotools PKG_CHECK_MODULES 构建期把 API 桩化）机制不同：
本条是 qmake configure.json 插件级裁剪，库本体无桩、行为面有文档定义，测试方法论
（白名单+签名双闸豁免、消费者断言补全）是增量。

## 方案：裁剪交给探测 + 测试双闸划界 + 消费者断言锁定

### ① 裁剪不硬禁

qmake 直接构建（-spec linux-clang），configure.json 探测自然关闭 speechd/flite——
包内零插件、库本体完整。readelf -d 验证 NEEDED 链干净。

### ② 上游套件真跑 + 引擎白名单/文档化签名双校验

```python
_ENGINE_DEPENDENT_TESTS = {          # 审读上游测试源码圈定的引擎依赖用例
    "say_hello", "speech_rate", "pitch", "set_voice", "volume",
}
def _validate_engine_absence(self, suite, out, totals):
    if totals["failed"] == 0:
        return
    failed_funcs = re.findall(
        r"^(?:FAIL!|BFAIL|XPASS)\s*:\s*tst_QTextToSpeech::(\w+)\(\)", out, re.M)
    unexpected = [f for f in failed_funcs
                  if f not in self._ENGINE_DEPENDENT_TESTS]
    if unexpected:
        raise ConanException(        # 白名单外的失败 = 真实缺陷，立即失败
            f"... failed outside the engine-dependent test set ...")
    if "No text-to-speech plug-ins were found." not in out:
        raise ConanException(        # 白名单内失败也必须携带文档化签名
            f"... failed without the documented no-engine signature")
```

双闸缺一不可：白名单圈「哪些用例可失败」，签名锁定「为何失败」。上游 BLACKLIST
拉黑项（speech_rate/set_voice 为上游 `*` 条目全平台拉黑）如实计入统计、不计为失败。

### ③ test_package 12 组无引擎行为面断言（文档化契约逐项锁定）

availableEngines 为空 / state()==BackendError / null-guarded say-stop-pause-resume 状态
不变 / rate-pitch-volume 0.0 默认值 / 空 voices-locales + 默认构造 locale / 无引擎
setter 不发射 changed 信号 / QVoice 值语义（默认构造-拷贝相等-genderName/ageName-受护
setter 镜像）——每断言带唯一退出码 1-12，失败可精确定位。

完整实现：PR !14839 archives/q/qt5-qtspeech/5.15.2/（conanfile.py 双闸 +
test_package/test.cpp 12 断言）。

## 回退

上游无可圈白名单（用例全引擎依赖/失败集不稳定）→ 退化为只跑引擎无关引导用例
（initTestCase/cleanupTestCase）+ PR 正文如实申报环境限制并附签名原文；再不济跳过上游
套件仅保 test_package 断言（统计如实写明）。若后端可自行合成（不依赖系统服务），首选
补 mock/回声引擎插件而非裁剪——本条仅适用「后端是平台系统服务且 OHOS 确无」的场景。

## 验证（PR !14839）

- 上游 texttospeech 套件真跑：`Totals: 2 passed, 3 failed, 0 skipped, 2 blacklisted`——
  3 失败全部携带文档化签名、双闸通过；0 意外失败
- 上游 cmake 套件 1/1 module_includes PASS；test_package 12 断言 PASS
- 本地 CI 同款脚本 build_and_test.sh（zsh）G0/KC/JC/L0-L5 全 pass，Build Summary 100.0%（1/1）

## 推广价值

一切「上游依赖平台系统服务而后端在 OHOS 缺位」的模块：打印（cups 无）、蓝牙（bluez
栈差异）、传感器（hal 层缺位）、通知（freedesktop dbus 服务缺位）、输入法等同类——
裁剪交给探测、测试划界用白名单+签名双闸、消费者侧把文档化无后端行为面逐项断言锁定，
三件套方法论直接横移。

## 关系

- 同族差异：E550 族（可选依赖静默降级，构建期 API 桩化）与
  DRAFT-ohos-optional-dep-silent-degrade-stub-api——本条机制（qmake configure.json
  插件裁剪）与测试方法论（双闸豁免+消费者断言）均为增量
- E596/E598（test_package 消费者证明形态）讲「证明库可用」，本条讲「证明无后端时
  行为面符合文档」——断言对象互补
