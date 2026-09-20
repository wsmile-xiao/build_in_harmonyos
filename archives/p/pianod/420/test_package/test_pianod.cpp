// test_pianod2.cpp — consumer test for the packaged pianod2 application.
//
// Two layers, both driven against the *packaged* binary:
//   1. link/introspection: `pianod -v -v` reports the compile/runtime version of
//      every library pianod was linked against, so each assertion pins a real
//      dependency (curl, OpenSSL, gstreamer, taglib, the three sources).
//   2. runtime service (R40): start the daemon on a loopback port, speak the
//      documented line protocol and assert on the greeting/session payload —
//      proving the ELF really runs and serves on HarmonyOS, not merely links.
//      The web client dir has to be passed explicitly because the recipe builds
//      with --prefix=/ (so conan's DESTDIR install lands cleanly in <pkg>/bin);
//      the compiled-in DEFAULT_WWWDIR therefore cannot be a package-relative
//      path. PIANOD_WWWDIR is injected by CMake at build time.
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <netinet/in.h>
#include <unistd.h>

#include <cerrno>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#ifndef PIANOD_WWWDIR
#define PIANOD_WWWDIR ""
#endif

namespace {

int failures = 0;
int checks = 0;
int skips = 0;

std::string
capture(const char* command)
{
    std::string out;
    FILE* pipe = popen(command, "r");
    if (pipe == nullptr)
        return out;
    char buffer[256];
    while (fgets(buffer, sizeof(buffer), pipe) != nullptr)
        out += buffer;
    pclose(pipe);
    return out;
}

void
expectContains(const std::string& haystack, const char* needle, const char* what)
{
    ++checks;
    if (haystack.find(needle) == std::string::npos) {
        ++failures;
        std::fprintf(stderr, "FAIL: %s (missing \"%s\")\n", what, needle);
    }
    else {
        std::printf("ok: %s\n", what);
    }
}

// Start the daemon, talk the line protocol, assert the payload, then stop it.
void
verifyLiveService(const std::string& stateDir, int port)
{
    const std::string logPath = stateDir + "/pianod-test.log";
    std::string start = "pianod -d " + stateDir + " -c " PIANOD_WWWDIR " -p " + std::to_string(port)
        + " -P 0 -s 0 -T >" + logPath + " 2>&1 & echo $!";

    const std::string pidText = capture(start.c_str());
    pid_t pid = static_cast<pid_t>(strtol(pidText.c_str(), nullptr, 10));
    if (pid <= 0) {
        ++failures;
        std::fprintf(stderr, "FAIL: could not launch packaged pianod (pid=%ld)\n", (long)pid);
        std::fprintf(stderr, "%s", capture(("cat " + logPath).c_str()).c_str());
        return;
    }

    int fd = -1;
    for (int attempt = 0; attempt < 25 && fd < 0; ++attempt) {
        usleep(200 * 1000);
        fd = socket(AF_INET, SOCK_STREAM, 0);
        if (fd < 0)
            continue;
        sockaddr_in addr {};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(static_cast<uint16_t>(port));
        addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        if (connect(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
            close(fd);
            fd = -1;
        }
    }

    ++checks;
    if (fd < 0) {
        ++failures;
        std::fprintf(stderr, "FAIL: daemon did not accept a connection on port %d\n", port);
        std::fprintf(stderr, "%s", capture(("cat " + logPath).c_str()).c_str());
        kill(pid, SIGTERM);
        waitpid(pid, nullptr, 0);
        return;
    }
    std::printf("ok: daemon accepts TCP connections on port %d\n", port);

    // pianod greets unauthenticated sessions; ?status is answered once attached.
    std::string banner;
    char buffer[1024];
    for (int round = 0; round < 3; ++round) {
        ssize_t got = read(fd, buffer, sizeof(buffer) - 1);
        if (got > 0) {
            buffer[got] = '\0';
            banner += buffer;
        }
        if (banner.find("Idle") != std::string::npos)
            break;
        usleep(250 * 1000);
    }
    close(fd);
    kill(pid, SIGTERM);
    waitpid(pid, nullptr, 0);

    expectContains(banner, "200 Success", "line protocol answers with 200 Success");
    expectContains(banner, "pianod2 420", "live daemon reports upstream r420");
    expectContains(banner, "Privileges:", "session privileges are negotiated");
    expectContains(banner, "SelectedSource", "media manager exposes a session state");
}

} // namespace

int
main()
{
    const std::string banner = capture("pianod -v 2>&1");
    expectContains(banner, "pianod2 version 420", "packaged pianod reports upstream r420");

    const std::string detail = capture("pianod -v -v 2>&1");
    expectContains(detail, "SSL package: OpenSSL", "OpenSSL TLS transport linked (football)");
    expectContains(detail, "curl compile version", "libcurl linked for the Pandora source");
    expectContains(detail, "curl runtime version", "libcurl resolves at runtime (shared)");
    expectContains(detail, "gstreamer library", "gstreamer media engine linked");
    expectContains(detail, "compile version 1.13", "taglib metadata reader linked");
    expectContains(detail, "pandora", "Pandora source compiled in");
    expectContains(detail, "filesystem", "filesystem source compiled in");
    expectContains(detail, "tonegenerator", "tone generator source compiled in");

    const std::string usage = capture("pianod -? 2>&1");
    expectContains(usage, "httpsport", "TLS listener option advertised");

    if (std::string(PIANOD_WWWDIR).empty()) {
        ++skips;
        std::printf("SKIP: live service check (PIANOD_WWWDIR not provided)\n");
    }
    else {
        std::string stateDir = "pianod2-test-state";
        capture(("rm -rf " + stateDir + " && mkdir -p " + stateDir).c_str());
        verifyLiveService(stateDir, 14471);
    }

    std::printf("\nChecks run: %d, passed: %d, skipped: %d\n", checks, checks - failures, skips);
    if (failures != 0) {
        std::fprintf(stderr, "Test failed: %d/%d checks failed.\n", failures, checks);
        return 1;
    }
    std::printf("All tests passed.\n");
    return 0;
}
