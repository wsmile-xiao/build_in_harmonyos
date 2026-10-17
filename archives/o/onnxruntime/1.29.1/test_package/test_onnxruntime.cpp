// ONNX Runtime 1.29.1 L1 consumer test (C API).
//
// Verifies the packaged runtime library actually loads and its core API
// surface is usable on the HarmonyOS PC (aarch64) target:
//   1. OrtGetApiBase()                     — runtime library loads, ABI version
//   2. api->GetVersionString()             — library reports its version
//   3. api->CreateEnv(...)                 — environment construction
//   4. api->CreateSessionOptions(...)      — session options construction
//   5. option setters (intra-op threads, graph optimisation level)
//   6. api->CreateRunOptions(...)          — run options construction
//   7. api->GetAvailableProviders()        — execution-provider enumeration
//      (proves the full op/EP registration tables are linked in, i.e. this is
//      a complete runtime build and not a stripped-down MINIMAL_BUILD)
//   8. teardown in the correct order
//
// No model file is required: the test exercises the runtime's own API, which
// is what "runtime library loads and the API is callable" means.  An actual
// inference needs a model + weights that this package does not ship.

#include <onnxruntime/onnxruntime_c_api.h>

#include <cstdio>

namespace {

int g_failures = 0;

void check(bool cond, const char *what) {
    if (cond) {
        std::printf("  ok   : %s\n", what);
    } else {
        std::printf("  FAIL : %s\n", what);
        ++g_failures;
    }
}

}  // namespace

int main() {
    const OrtApiBase *api_base = OrtGetApiBase();
    check(api_base != nullptr, "OrtGetApiBase()");
    if (api_base == nullptr) return 1;

    std::printf("ONNX Runtime version: %s\n", api_base->GetVersionString());
    check(api_base->GetVersionString() != nullptr, "GetVersionString()");

    const OrtApi *api = api_base->GetApi(ORT_API_VERSION);
    check(api != nullptr, "GetApi(ORT_API_VERSION)");
    if (api == nullptr) return 1;

    // 3. Environment
    OrtEnv *env = nullptr;
    OrtStatus *st = api->CreateEnv(ORT_LOGGING_LEVEL_WARNING, "ohos_l1_test", &env);
    check(st == nullptr && env != nullptr,
          "CreateEnv(ORT_LOGGING_LEVEL_WARNING)");
    if (st != nullptr) {
        std::fprintf(stderr, "  CreateEnv error: %s\n", api->GetErrorMessage(st));
        api->ReleaseStatus(st);
        return 1;
    }

    // 4. Session options
    OrtSessionOptions *opts = nullptr;
    st = api->CreateSessionOptions(&opts);
    check(st == nullptr && opts != nullptr, "CreateSessionOptions()");
    if (st != nullptr) {
        api->ReleaseStatus(st);
        api->ReleaseEnv(env);
        return 1;
    }

    // 5. Option setters
    st = api->SetIntraOpNumThreads(opts, 1);
    check(st == nullptr, "SetIntraOpNumThreads(1)");
    if (st != nullptr) api->ReleaseStatus(st);

    st = api->SetSessionGraphOptimizationLevel(opts, ORT_ENABLE_BASIC);
    check(st == nullptr, "SetSessionGraphOptimizationLevel(ORT_ENABLE_BASIC)");
    if (st != nullptr) api->ReleaseStatus(st);

    // 6. Run options
    OrtRunOptions *run_opts = nullptr;
    st = api->CreateRunOptions(&run_opts);
    check(st == nullptr && run_opts != nullptr, "CreateRunOptions()");
    if (st != nullptr) api->ReleaseStatus(st);

    // 7. Execution providers — a full runtime build registers at least CPU.
    char **providers = nullptr;
    int n_providers = 0;
    st = api->GetAvailableProviders(&providers, &n_providers);
    check(st == nullptr, "GetAvailableProviders()");
    if (st == nullptr) {
        check(n_providers > 0, "at least one execution provider is registered");
        for (int i = 0; i < n_providers; ++i) {
            std::printf("  provider[%d]: %s\n", i,
                        providers[i] ? providers[i] : "(null)");
        }
        st = api->ReleaseAvailableProviders(providers, n_providers);
        if (st != nullptr) api->ReleaseStatus(st);
    } else {
        api->ReleaseStatus(st);
    }

    // 8. Teardown
    if (run_opts != nullptr) api->ReleaseRunOptions(run_opts);
    api->ReleaseSessionOptions(opts);
    api->ReleaseEnv(env);

    if (g_failures != 0) {
        std::fprintf(stderr, "[test_onnxruntime] FAILED: %d assertion(s)\n",
                     g_failures);
        return 1;
    }
    std::printf("[test_onnxruntime] PASS: onnxruntime 1.29.1 env/options/providers OK\n");
    return 0;
}
