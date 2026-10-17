// test_package/test_hermes.cpp
// L1 test: run the hermes binary to execute a simple JS program
// This verifies the hermes package's binary is functional (R34)
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

int main() {
    // Get hermes binary path from compile definition
    const char* hermes_bin = HERMES_BIN_PATH;
    if (!hermes_bin || strlen(hermes_bin) == 0) {
        fprintf(stderr, "ERROR: HERMES_BIN_PATH not defined\n");
        return 1;
    }

    // Create a simple JS test file in current directory (writable)
    const char* jsfile = "test_hermes_check.js";
    FILE* js = fopen(jsfile, "w");
    if (!js) {
        fprintf(stderr, "ERROR: Cannot create JS test file\n");
        return 1;
    }
    fprintf(js, "print('Hello from Hermes!');\n");
    fclose(js);

    // Run hermes binary with the JS file
    std::string cmd = std::string(hermes_bin) + " " + jsfile;
    int rc = system(cmd.c_str());

    // Cleanup
    remove(jsfile);

    if (rc != 0) {
        fprintf(stderr, "ERROR: hermes binary exited with code %d\n", rc);
        return 1;
    }

    printf("Hermes binary test: PASS\n");
    return 0;
}
