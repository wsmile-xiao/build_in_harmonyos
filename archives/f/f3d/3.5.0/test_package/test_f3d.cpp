// f3d test_package source — verifies the packaged binary really runs.
// R34: test_package must actually exercise the built package.
// Strategy:
//   1. Verify the package ships a valid ELF binary at bin/f3d.
//   2. EXECUTE it: `f3d --version` must exit 0 and print a version
//      string starting with "f3d 3." (the upstream version output).
//      Rendering options are not exercised (they need a GPU context);
//      --version is a real execution of the packaged binary which
//      exercises dynamic loading of libf3d.so + all VTK shared libs
//      through the loader (this is exactly what the SONAME/re-sign
//      adaptation work guarantees).
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
    std::string f3d_path = (argc > 1) ? std::string(argv[1]) : std::string("f3d");

    // 1) binary exists?
    std::ifstream f(f3d_path, std::ios::binary);
    if (!f.is_open()) {
        const char* pkg_folder = std::getenv("CONAN_PACKAGE_FOLDER_f3d");
        if (pkg_folder) {
            f3d_path = std::string(pkg_folder) + "/bin/f3d";
            f.open(f3d_path, std::ios::binary);
        }
    }
    if (!f.is_open()) {
        std::cerr << "FAIL: f3d binary not found at '" << f3d_path << "'" << std::endl;
        return EXIT_FAILURE;
    }

    // 2) valid ELF?
    char magic[4] = {0, 0, 0, 0};
    f.read(magic, 4);
    std::streamsize bytes_read = f.gcount();
    f.seekg(0, std::ios::end);
    long size = f.tellg();
    f.close();
    if (bytes_read < 4 || magic[0] != 0x7f || magic[1] != 'E' || magic[2] != 'L' || magic[3] != 'F') {
        std::cerr << "FAIL: file at '" << f3d_path << "' is not a valid ELF binary" << std::endl;
        return EXIT_FAILURE;
    }
    if (size < 1024) {
        std::cerr << "FAIL: f3d binary too small (" << size << " bytes) — likely truncated" << std::endl;
        return EXIT_FAILURE;
    }

    // 3) EXECUTE the packaged binary and validate its output.
    //    f3d --version prints "F3D 3.5.0" and exits 0 on success.
    std::string cmd = f3d_path + " --version 2>&1";
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) {
        std::cerr << "FAIL: cannot execute '" << f3d_path << "' (popen failed)" << std::endl;
        return EXIT_FAILURE;
    }
    std::string output;
    char buf[256];
    while (fgets(buf, sizeof(buf), pipe) != nullptr) {
        output += buf;
    }
    int rc = pclose(pipe);

    std::cout << "f3d --version output: " << output;
    if (rc != 0) {
        std::cerr << "FAIL: 'f3d --version' exited with code " << rc
                  << " — the packaged binary does not run" << std::endl;
        return EXIT_FAILURE;
    }
    if (output.find("F3D 3.") == std::string::npos) {
        std::cerr << "FAIL: 'f3d --version' output does not contain a version string" << std::endl;
        return EXIT_FAILURE;
    }

    std::cout << "PASS: f3d binary executed successfully (" << size << " bytes, ELF, exit 0, version output verified)" << std::endl;
    return EXIT_SUCCESS;
}
