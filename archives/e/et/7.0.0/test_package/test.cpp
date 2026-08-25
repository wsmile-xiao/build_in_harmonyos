// test_package for et/7.0.0
//
// et ships only executables (et, etserver, etterminal, htm, htmd).
// This test verifies that the `et` binary exists in the package
// folder and can be launched with --version (or --help) without
// crashing.
//
// We use fork/execvp/waitpid directly (NOT std::system) so that
// waitpid returns the wait status of the et child process itself,
// and WIFSIGNALED/WIFEXITED correctly reflect whether et crashed
// or exited normally. With std::system the returned status is that
// of the intermediate /bin/sh, which folds signal-killed children
// into a 128+N normal exit, making crash detection impossible.
//
// Exit codes:
//   0 = et binary found and launched successfully (--version or
//       --help returned 0, or returned non-zero via normal exit)
//   1 = et binary not found at the resolved path
//   2 = et --version AND --help both failed abnormally (process
//       killed by signal, or could not be executed at all)

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include <unistd.h>     // fork, execvp, _exit, dup2
#include <sys/wait.h>   // waitpid, WIFSIGNALED, WIFEXITED, WEXITSTATUS
#include <fcntl.h>      // open, O_WRONLY

static bool file_exists(const char *path) {
    FILE *f = std::fopen(path, "rb");
    if (!f) return false;
    std::fclose(f);
    return true;
}

// Outcome of a single et invocation.
enum class Outcome {
    ExitedZero,      // et exited normally with status 0
    ExitedNonZero,   // et exited normally with non-zero status
    Signaled,        // et was killed by a signal (crash)
    CannotStart,     // fork/exec failed — et could not be started
};

// Run et with the given argv (argv[0] = path to et).
// Redirects stdout/stderr to /dev/null so the test output is clean.
static Outcome run_et(const std::string &et_path, const char *arg) {
    pid_t pid = fork();
    if (pid < 0) {
        return Outcome::CannotStart;  // fork failed
    }
    if (pid == 0) {
        // Child: redirect stdout/stderr to /dev/null
        int devnull = open("/dev/null", O_WRONLY);
        if (devnull >= 0) {
            dup2(devnull, STDOUT_FILENO);
            dup2(devnull, STDERR_FILENO);
            close(devnull);
        }
        // execvp so we get the real child wait status
        char *argv[] = {
            const_cast<char *>(et_path.c_str()),
            const_cast<char *>(arg),
            nullptr,
        };
        execvp(et_path.c_str(), argv);
        // If execvp returns, it failed (errno set).
        _exit(127);  // convention: 127 = command not found / exec failed
    }
    // Parent: wait for the et child (NOT a shell)
    int status = 0;
    if (waitpid(pid, &status, 0) < 0) {
        return Outcome::CannotStart;  // waitpid failed
    }
    if (WIFSIGNALED(status)) {
        return Outcome::Signaled;     // et crashed (signal)
    }
    if (WIFEXITED(status)) {
        int code = WEXITSTATUS(status);
        if (code == 127 || code == 126) {
            // exec failed in child (127) or permission denied (126)
            return Outcome::CannotStart;
        }
        return (code == 0) ? Outcome::ExitedZero
                           : Outcome::ExitedNonZero;
    }
    // Should not happen (neither signaled nor exited)
    return Outcome::CannotStart;
}

int main() {
    // The test_package conanfile sets ET_BIN_DIR to the et package's
    // bin/ directory. Fallback to CONAN_PACKAGE_FOLDER/bin or "et".
    std::string et_path;
    const char *et_bin_dir = std::getenv("ET_BIN_DIR");
    if (et_bin_dir && et_bin_dir[0]) {
        et_path = std::string(et_bin_dir) + "/et";
    } else {
        const char *pkg_folder = std::getenv("CONAN_PACKAGE_FOLDER");
        if (pkg_folder && pkg_folder[0]) {
            et_path = std::string(pkg_folder) + "/bin/et";
        } else {
            et_path = "et";
        }
    }

    if (!et_path.empty() && !file_exists(et_path.c_str())) {
        std::fprintf(stderr, "ERROR: et binary not found at %s\n",
                     et_path.c_str());
        return 1;
    }

    // Launch et --version. Remote terminal tools print version on
    // --version and exit 0; some exit non-zero on unknown flags.
    Outcome result = run_et(et_path, "--version");

    // Only retry with --help if --version exited non-zero (not a
    // signal/cannot-start failure — those are terminal).
    if (result == Outcome::ExitedNonZero) {
        result = run_et(et_path, "--help");
    }

    switch (result) {
        case Outcome::ExitedZero:
        case Outcome::ExitedNonZero:
            // et launched and exited normally (0 or non-zero).
            // CLI tools may reject unknown flags; that's acceptable.
            std::printf("et test_package: binary launched and exited "
                        "normally\n");
            return 0;
        case Outcome::Signaled:
            std::fprintf(stderr, "ERROR: et was killed by a signal "
                                 "(crash)\n");
            return 2;
        case Outcome::CannotStart:
            std::fprintf(stderr, "ERROR: et could not be executed "
                                 "(exec/fork failed)\n");
            return 2;
    }
    // Unreachable, but silence compiler warnings
    return 2;
}
