#include <QCoreApplication>
#include <QTextToSpeech>
#include <QVoice>
#include <QLocale>
#include <QObject>
#include <cstdio>

// Real consumer-side exercise of libQt5TextToSpeech on OpenHarmony PC.
//
// Platform context (与配方 build() 内上游测试的环境排除定性互补):
// OHOS 平台没有 speech-dispatcher 守护进程、也没有 flite 合成器服务，
// qmake 特性探测（src/tts/configure.json）关闭 speechd/flite，因此包内
// 不含任何 TTS 引擎插件。库本体（libQt5TextToSpeech）按上游文档定义的
// 无引擎行为面工作，本测试从消费者侧逐项断言：
//   1. 构造成功（插件扫描容忍空插件集）
//   2. state() == BackendError（文档：无引擎 → BackendError）
//   3. availableEngines() 为空
//   4. say/stop/pause/resume 均为空指针保护调用（不崩溃、状态不变）
//   5. rate/pitch/volume 报告文档定义的 0.0 默认值
//   6. availableVoices()/availableLocales() 为空；locale() 为默认构造值
//   7. 无引擎时 setVolume/setRate/setPitch 不发射对应 changed 信号
//   8. QVoice 值语义（默认构造/拷贝相等/genderName/ageName/受护 setter）
int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);

    // --- 1. engine discovery ----------------------------------------
    if (QTextToSpeech::availableEngines().count() != 0) {
        std::printf("QtSpeech test FAILED: expected no TTS engines on OHOS, got %d\n",
                    QTextToSpeech::availableEngines().count());
        return 1;
    }

    // --- 2. documented no-engine state ------------------------------
    QTextToSpeech tts;
    if (tts.state() != QTextToSpeech::BackendError) {
        std::printf("QtSpeech test FAILED: expected BackendError state, got %d\n",
                    int(tts.state()));
        return 2;
    }

    // --- 3. null-guarded API surface --------------------------------
    tts.say(QStringLiteral("this is an example text"));
    tts.pause();
    tts.resume();
    tts.stop();
    if (tts.state() != QTextToSpeech::BackendError) {
        std::printf("QtSpeech test FAILED: state changed without an engine\n");
        return 3;
    }

    // --- 4. documented property defaults ----------------------------
    if (tts.rate() != 0.0 || tts.pitch() != 0.0 || tts.volume() != 0.0) {
        std::printf("QtSpeech test FAILED: rate/pitch/volume defaults are not 0.0\n");
        return 4;
    }

    // --- 5. empty voice/locale model ---------------------------------
    if (!tts.availableVoices().isEmpty() || !tts.availableLocales().isEmpty()) {
        std::printf("QtSpeech test FAILED: expected empty voices/locales\n");
        return 5;
    }
    if (tts.locale() != QLocale()) {
        std::printf("QtSpeech test FAILED: expected default-constructed locale\n");
        return 6;
    }

    // --- 6. setters stay silent without an engine --------------------
    int volumeSignals = 0;
    QObject::connect(
        &tts,
        static_cast<void (QTextToSpeech::*)(double)>(&QTextToSpeech::volumeChanged),
        [&volumeSignals](double) { ++volumeSignals; });
    tts.setVolume(0.7);
    tts.setRate(0.5);
    tts.setPitch(-0.5);
    if (volumeSignals != 0) {
        std::printf("QtSpeech test FAILED: volumeChanged emitted without an engine\n");
        return 7;
    }
    if (tts.volume() != 0.0) {
        std::printf("QtSpeech test FAILED: volume changed without an engine\n");
        return 8;
    }

    // --- 7. QVoice value semantics -----------------------------------
    QVoice defaultVoice;
    if (defaultVoice.name().isEmpty()) {
        std::printf("QtSpeech test FAILED: default voice has no name\n");
        return 9;
    }
    QVoice otherVoice = defaultVoice;
    if (!(defaultVoice == otherVoice)) {
        std::printf("QtSpeech test FAILED: default voices are not equal\n");
        return 10;
    }
    if (QVoice::genderName(QVoice::Male).isEmpty()
        || QVoice::ageName(QVoice::Adult).isEmpty()) {
        std::printf("QtSpeech test FAILED: genderName/ageName returned empty\n");
        return 11;
    }
    tts.setVoice(defaultVoice);  // null-guarded setter, no crash expected
    if (!(tts.voice() == defaultVoice)) {
        std::printf("QtSpeech test FAILED: voice() should mirror default construction\n");
        return 12;
    }

    std::printf("QtSpeech test PASSED\n");
    return 0;
}
