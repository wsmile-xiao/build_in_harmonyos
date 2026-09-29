#include <MAdLib.h>

int main(int argc, char **argv) {
    if (argc < 1 || argv == nullptr || argv[0] == nullptr) return 2;
    const int initial_argc = argc;
    MAdLibInitialize(&argc, &argv);
    if (argc != initial_argc) return 3;
    MAdLibFinalize();
    return 0;
}
