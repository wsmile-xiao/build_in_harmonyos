#include <kylin-ai/common/common.h>
#include <kylin-ai/common/error.h>
#include <kylin-ai/common/enums.h>

#include <cstdio>

// Consumer smoke test: links against kysdk-ai-common and exercises its public API.
// is_ai_subsystem_inited() must return false when the AI subsystem has not been
// initialized in this process (upstream src/common.cpp returns false by default).
int main() {
    AiSdkCommonErrorCode err = AISDK_NO_ERROR;
    ModelDeployType deploy = OnDevice;

    if (err != AISDK_NO_ERROR) {
        std::fprintf(stderr, "unexpected error code value\n");
        return 1;
    }
    if (deploy != OnDevice) {
        std::fprintf(stderr, "unexpected deploy type value\n");
        return 1;
    }
    if (is_ai_subsystem_inited()) {
        std::fprintf(stderr, "AI subsystem should NOT be inited in a fresh process\n");
        return 1;
    }
    std::printf("test kysdk-ai-common 1.1.0.1: OK\n");
    return 0;
}
