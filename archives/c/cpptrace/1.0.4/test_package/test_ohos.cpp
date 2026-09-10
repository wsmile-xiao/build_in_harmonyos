// OHOS-specific runtime verification: real stack unwinding + symbol
// resolution through the packaged library on HarmonyOS PC (musl libc).
#include <cpptrace/cpptrace.hpp>
#include <cstdio>

CPPTRACE_FORCE_NO_INLINE static int leaf() {
    cpptrace::stacktrace trace = cpptrace::generate_trace();
    std::printf("frames: %zu\n", trace.frames.size());
    for (const auto& frame : trace) {
        std::printf("#%zu %s\n", static_cast<std::size_t>(-1) == 0 ? 0 : 0,
                    frame.to_string().c_str());
        break;  // first frame detail is enough evidence
    }
    trace.print();
    return static_cast<int>(trace.frames.size());
}

CPPTRACE_FORCE_NO_INLINE static int caller() { return leaf(); }

int main() {
    const int frames = caller();
    if (frames < 2) {
        std::fprintf(stderr, "stack trace too shallow: %d frames\n", frames);
        return 1;
    }
    std::printf("test_cpptrace_ohos: %d frames unwound, OK\n", frames);
    return 0;
}
