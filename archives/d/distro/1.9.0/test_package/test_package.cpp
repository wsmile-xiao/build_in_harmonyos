// test_package.cpp — consumer-side test for the distro 1.9.0 package.
//
// distro is a pure-Python package (no C/C++ library), so this test verifies
// the installed module through the conanrun environment: package_info() sets
// PYTHONPATH to the site-packages inside the package folder, letting python3
// import the "distro" module shipped by the package under test.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

static bool run_python(const char* expr, std::string* out) {
    // Build: python3 -c "<expr>"
    std::string cmd = "python3 -c \"";
    cmd += expr;
    cmd += "\"";
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) {
        return false;
    }
    char buf[512];
    std::string result;
    while (fgets(buf, sizeof(buf), pipe) != nullptr) {
        result += buf;
    }
    int rc = pclose(pipe);
    if (rc != 0) {
        return false;
    }
    if (out) {
        *out = result;
    }
    return true;
}

int main() {
    // 1) Module must be importable (PYTHONPATH from package_info).
    std::string ver;
    if (!run_python("import distro; print(distro.__version__)", &ver)) {
        std::fprintf(stderr, "[FAIL] distro module import failed\n");
        return 1;
    }
    std::string trimmed;
    for (char c : ver) {
        if (c == '\n' || c == ' ') {
            continue;
        }
        trimmed += c;
    }
    if (trimmed != "1.9.0") {
        std::fprintf(stderr, "[FAIL] unexpected distro version: '%s'\n",
                     trimmed.c_str());
        return 2;
    }

    // 2) Module must be able to query the running OS distribution.
    std::string distro_id;
    if (!run_python("import distro; print(distro.id())", &distro_id)) {
        std::fprintf(stderr, "[FAIL] distro.id() call failed\n");
        return 3;
    }

    std::printf("distro 1.9.0 assertions: 2 passed (version=%s id=%s)",
                trimmed.c_str(), distro_id.c_str());
    return 0;
}