#include <mgl2/mgl.h>

#include <cstdio>

int main() {
    const char *path = "mathgl-consumer.png";
    {
        mglGraph graph(0, 64, 64);
        graph.FPlot("sin(pi*x)");
        graph.WritePNG(path);
    }
    std::FILE *file = std::fopen(path, "rb");
    if (file == nullptr) return 2;
    unsigned char signature[8] = {};
    const std::size_t count = std::fread(signature, 1, sizeof(signature), file);
    std::fclose(file);
    const unsigned char expected[8] = {137, 80, 78, 71, 13, 10, 26, 10};
    if (count != sizeof(signature)) return 3;
    for (unsigned int i = 0; i < sizeof(signature); ++i)
        if (signature[i] != expected[i]) return 4;
    std::puts("MATHGL_PNG_OK");
    return 0;
}
