// test_package/test.cpp — R34: substantive nativefiledialog-extended API test.
//
// Headless-safe smoke over the error API surface:
//   1. NFD_GetError() is NULL before any call;
//   2. NFD_ClearError() is a safe no-op at any time.
// Compiling and linking against libnfd plus the full GTK3 shared chain (and
// loading it at runtime) is the primary verification target.
//
// Deliberately NOT called here (both need a live GTK display; declared in
// test_package/MANIFEST.yml):
//   - NFD_Init/NFD_Quit: on OHOS the GTK broadway backend blocks inside
//     gtk_init_check when no display is available (实测：无论 GDK_BACKEND
//     预设与否，init 均不返回，OHOS PC 无显示环境下的平台行为) — running it
//     headless would hang the test instead of failing fast;
//   - dialog UI (NFD_OpenDialog etc.): cannot run headless by design.
#include <nfd.h>

#include <cstdio>

static int failures = 0;

#define CHECK(cond, msg)                          \
    do {                                          \
        if (!(cond)) {                            \
            std::printf("FAIL: %s\n", msg);       \
            ++failures;                           \
        }                                         \
    } while (0)

int main() {
    // 1. Fresh state: no error pending.
    CHECK(NFD_GetError() == nullptr, "initial NFD_GetError must be NULL");

    // 2. ClearError must be safe to call at any time (no error yet).
    NFD_ClearError();
    CHECK(NFD_GetError() == nullptr,
          "NFD_ClearError must keep state clean (no error recorded)");

    if (failures != 0) {
        std::printf("nativefiledialog-extended test_package: FAILED (%d)\n",
                    failures);
        return 1;
    }
    std::printf("nativefiledialog-extended test_package: OK (2 checks)\n");
    return 0;
}
