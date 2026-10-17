// Conan test_package for layer-shell-qt 6.7.2.
// Real API usage (R34): links an exported LayerShellQt API symbol
// (LayerShellQt::Shell::useLayerShell from libLayerShellQtInterface) so the
// consumer link is genuinely exercised. The symbol's address is resolved at
// link time; on a headless OHOS build we must not call into Wayland, so only
// the address is taken (no compositor connection is opened).
#include <LayerShellQt/Shell>
#include <cstdio>

// useLayerShell is marked deprecated since 6.6 upstream; taking its address
// is still valid and proves the exported symbol links. Silence the warning.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"

int main() {
    auto fn = &LayerShellQt::Shell::useLayerShell;
    if (!fn) {
        std::printf("FAIL: LayerShellQt::Shell::useLayerShell symbol missing\n");
        return 1;
    }
    std::printf("LayerShellQt 6.7.2: headers OK, exported symbol useLayerShell at %p\n",
                (void *)fn);
    return 0;
}
#pragma GCC diagnostic pop
