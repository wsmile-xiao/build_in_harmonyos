#include <cstdio>
#include <cstring>

int main()
{
    FILE *pipe = popen("wdq2wav -h", "r");
    if (pipe == nullptr) {
        std::fputs("failed to execute wdq2wav -h\n", stderr);
        return 1;
    }

    char buffer[4096];
    const std::size_t bytes_read = std::fread(buffer, 1, sizeof(buffer) - 1, pipe);
    buffer[bytes_read] = '\0';
    const int rc = pclose(pipe);
    if (rc != 0) {
        std::fprintf(stderr, "wdq2wav -h exited with status %d\n", rc);
        return 2;
    }

    if (std::strstr(buffer, "usage:") == nullptr ||
        std::strstr(buffer, "wdq-file") == nullptr ||
        std::strstr(buffer, "wav-file") == nullptr) {
        std::fprintf(stderr, "unexpected help output:\n%s\n", buffer);
        return 3;
    }

    std::puts("wdq2wav CLI help test: OK");
    return 0;
}