#include <dlfcn.h>
#include <security/pam_modules.h>

#include <cstdlib>
#include <iostream>

int main(int argc, char **argv) {
    if (argc != 2) {
        std::cerr << "usage: test_barada_pam <pam-module>\n";
        return EXIT_FAILURE;
    }

    void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (handle == nullptr) {
        std::cerr << "dlopen(pam_barada.so) failed: " << dlerror() << "\n";
        return EXIT_FAILURE;
    }

    using PamSetCred = int (*)(pam_handle_t *, int, int, const char **);
    auto setcred = reinterpret_cast<PamSetCred>(
        dlsym(handle, "pam_sm_setcred")
    );
    if (setcred == nullptr) {
        std::cerr << "pam_sm_setcred symbol is missing\n";
        dlclose(handle);
        return EXIT_FAILURE;
    }

    int result = setcred(nullptr, 0, 0, nullptr);
    if (result != PAM_CRED_UNAVAIL) {
        std::cerr << "unexpected pam_sm_setcred result: " << result << "\n";
        dlclose(handle);
        return EXIT_FAILURE;
    }

    dlclose(handle);
    std::cout << "barada-pam module load and PAM entry-point test passed\n";
    return EXIT_SUCCESS;
}
