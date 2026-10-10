#include <cstdio>
#include <string>
#include <sys/wait.h>

int main() {
    FILE *pipe = popen("qdirstat --help 2>&1", "r");
    if (!pipe) return 1;
    std::string output;
    char buffer[512];
    while (fgets(buffer, sizeof(buffer), pipe)) output += buffer;
    const int status = pclose(pipe);
    // Upstream intentionally exits 1 after printing usage.
    return WIFEXITED(status) && WEXITSTATUS(status) == 1 &&
                   output.find("Usage:") != std::string::npos
               ? 0
               : 2;
}
