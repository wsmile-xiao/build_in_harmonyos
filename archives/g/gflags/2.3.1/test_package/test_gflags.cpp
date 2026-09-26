#include <gflags/gflags.h>

#include <cstdio>
#include <string>

DEFINE_int32(answer, 0, "answer used by the package test");

int main() {
    const std::string result = gflags::SetCommandLineOption("answer", "42");
    if (result.empty()) {
        std::fprintf(stderr, "SetCommandLineOption failed\n");
        return 1;
    }
    if (FLAGS_answer != 42) {
        std::fprintf(stderr, "unexpected flag value: %d\n", FLAGS_answer);
        return 2;
    }
    std::printf("gflags answer=%d\n", FLAGS_answer);
    return 0;
}
