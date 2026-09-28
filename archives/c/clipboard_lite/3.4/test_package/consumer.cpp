// test_package consumer for clipboard_lite 3.4 (OHOS).
// R34: real consumer usage — includes ONLY the installed public header
// <Clipboard_Lite.h>, links libclipboard_lite, and drives the public API
// exactly as a downstream app would: CreateClipboard() -> onText() -> copy().
#include <Clipboard_Lite.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

int main()
{
    std::printf("clipboard_lite consumer: building clipboard manager\n");
    std::fflush(stdout);

    // Public API surface: factory + configuration + manager interfaces.
    auto clipboard = SL::Clipboard_Lite::CreateClipboard();
    if (!clipboard) {
        std::fprintf(stderr, "CreateClipboard() returned null\n");
        return 10;
    }
    std::printf("clipboard_lite consumer: CreateClipboard() ok\n");
    std::fflush(stdout);

    auto configured = clipboard
                          ->onText([](const std::string &text) {
                              std::printf("consumer: onText got %zu bytes\n", text.size());
                          })
                          ->onImage([](const SL::Clipboard_Lite::Image &image) {
                              std::printf("consumer: onImage w=%d h=%d stride=%d\n",
                                          image.Width, image.Height, image.PixelStride);
                          });
    if (!configured) {
        std::fprintf(stderr, "onText/onImage configuration failed\n");
        return 11;
    }
    std::printf("clipboard_lite consumer: onText/onImage registered\n");
    std::fflush(stdout);

    auto manager = configured->run();
    if (!manager) {
        std::fprintf(stderr, "run() returned null\n");
        return 12;
    }
    std::printf("clipboard_lite consumer: clipboard manager running\n");
    std::fflush(stdout);

    // Business-meaningful public API call: copy text into the clipboard.
    manager->copy(std::string("clipboard_lite consumer smoke text"));
    std::printf("clipboard_lite consumer: copy() submitted\n");
    std::fflush(stdout);
    std::printf("clipboard_lite consumer: OK\n");
    return 0;
}