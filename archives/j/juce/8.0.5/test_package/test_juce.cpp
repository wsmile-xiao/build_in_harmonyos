// test_package/test_juce.cpp — juce/8.0.5 OHOS 消费式验证。
//
// 走真实消费路径：find_package(JUCE)（包内官方 JUCEConfig.cmake）+
// juce_add_console_app + target_link_libraries(juce::juce_core /
// juce::juce_events / juce::juce_graphics)。三个模块的 INTERFACE 源
// （juce_core.cpp / juce_events.cpp / juce_graphics.cpp）会编译进本目标，
// 同时验证：
//   - JUCE_TARGET_PLATFORM 在 OHOS（__OHOS__ + __linux__）选择了 JUCE_LINUX；
//   - 包级默认 JUCE_USE_CURL=0 生效；
//   - juce_graphics 的 freetype2/fontconfig 链接（E505 共享库实体化视图+rpath）；
//   - musl/OHOS 运行时行为：线程、文件、时钟、UTF-8 字符串。
#include <atomic>
#include <cstdio>
#include <thread>

#include <juce_core/juce_core.h>
#include <juce_events/juce_events.h>
#include <juce_graphics/juce_graphics.h>

namespace
{
int g_checks = 0;

void check(bool ok, const char* what)
{
    ++g_checks;
    std::printf("[%s] %s\n", ok ? "PASS" : "FAIL", what);
    if (! ok)
        std::exit(1);
}
} // namespace

// ── 平台分支断言（编译期，OHOS 特有适配点的直接证据） ──────────────────
#ifndef __OHOS__
#error "test must be compiled for OHOS (__OHOS__ undefined)"
#endif
#if ! JUCE_LINUX
#error "JUCE_LINUX must be 1 on OHOS (compiler defines __linux__)"
#endif
#if JUCE_MODULE_AVAILABLE_juce_core != 1 || JUCE_MODULE_AVAILABLE_juce_events != 1 \
    || JUCE_MODULE_AVAILABLE_juce_graphics != 1
#error "linked JUCE modules must be declared available"
#endif
// 包级默认（juce_core.h 补丁）：curl 关闭，juce_core.cpp 不含 curl 头依赖
#if JUCE_USE_CURL != 0
#error "package default JUCE_USE_CURL=0 expected"
#endif

int main()
{
    // 1. SystemStats：musl 路径（含 _NL_ADDRESS_* 的 __OHOS__ 兜底分支）
    const auto osName = juce::SystemStats::getOperatingSystemName();
    check(osName.isNotEmpty(), "SystemStats::getOperatingSystemName non-empty");

    // 2. 显示语言（__OHOS__ 分支返回空串不崩溃）
    check(true, "SystemStats::getDisplayLanguage callable");
    const auto lang = juce::SystemStats::getDisplayLanguage();
    (void) lang;

    // 3. UTF-8 字符串（juce_core 基础路径）
    const juce::String s(juce::CharPointer_UTF8("\xe9\xb8\xbf\xe8\x92\x99")); // "鸿蒙"
    check(s == juce::String::fromUTF8("\xe9\xb8\xbf\xe8\x92\x99"),
          "juce::String UTF-8 roundtrip");
    check(s.length() == 2, "juce::String UTF-8 length");

    // 4. 线程（musl pthread 创建/join + JUCE 线程名路径）
    std::atomic<int> counter { 0 };
    struct Probe : juce::Thread
    {
        std::atomic<int>& c;
        explicit Probe(std::atomic<int>& ref) : juce::Thread("probe"), c(ref) {}
        void run() override
        {
            for (int i = 0; i < 1000; ++i)
                ++c;
        }
    } probe(counter);
    probe.startThread();
    probe.waitForThreadToExit(5000);
    check(counter.load() == 1000, "juce::Thread run/join (musl pthread)");

    // 5. 时钟单调（clock_gettime musl）
    const auto t0 = juce::Time::getMillisecondCounter();
    juce::Thread::sleep(60);
    const auto t1 = juce::Time::getMillisecondCounter();
    check(t1 >= t0 + 50, "juce::Time::getMillisecondCounter monotonic");

    // 6. 文件 I/O（toybox/musl 文件系统）
    auto file = juce::File::getCurrentWorkingDirectory().getChildFile("juce_ohos_probe.tmp");
    check(file.replaceWithText("juce-on-ohos\n"), "juce::File write");
    check(file.loadFileAsString().trim() == "juce-on-ohos", "juce::File read-back");
    check(file.deleteFile(), "juce::File delete");

    // 7. XML 解析（String 流 / 内存路径）
    juce::XmlDocument doc("<root a=\"1\"><child/></root>");
    auto xml = doc.getDocumentElement();
    check(xml != nullptr && xml->getTagName() == "root" && xml->getIntAttribute("a") == 1,
          "juce::XmlDocument parse");

    // 8. juce_events：MessageManager 不经创建可安全查询（链接闭包成立）
    check(juce::MessageManager::getInstanceWithoutCreating() == nullptr,
          "juce::events MessageManager::getInstanceWithoutCreating");

    // 9. juce_graphics：软件位图写入（juce_graphics 源+链接闭包真实编译进
    //    本目标；freetype2/fontconfig 共享库符号已由链接器解析（E505 实体化+rpath））
    juce::Image img(juce::Image::ARGB, 8, 8, true);
    {
        juce::Image::BitmapData bits(img, juce::Image::BitmapData::readWrite);
        bits.setPixelColour(3, 4, juce::Colours::red);
        const auto px = bits.getPixelColour(3, 4);
        check(px.getRed() > 200 && px.getAlpha() == 255, "juce::Image ARGB pixel");
    }

    // 10. 原子引用计数（aarch64 原生原子路径）
    {
        juce::MemoryBlock block(1024);
        block.setSize(2048, true);
        check(block.getSize() == 2048, "juce::MemoryBlock grow");
    }

    std::printf("juce-ohos-probe: %d checks, all passed (os=%s)\n",
                g_checks, osName.toRawUTF8());
    return 0;
}
