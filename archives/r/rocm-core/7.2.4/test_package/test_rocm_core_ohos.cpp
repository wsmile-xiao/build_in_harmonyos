// HarmonyOS-specific COMPLETE consumer flows for rocm-core/7.2.4 (rule 12).
//
// This file is not an assertion list. It implements three named complete
// consumer end-to-end cases; each performs the full flow a downstream ROCm
// component runs against an OHOS installation:
//
//     construct the input -> call the packaged API -> consume the returned
//     data with real file I/O on the installation tree -> emit a verifiable
//     result
//
//   HC-1 安装树发现与真实产物消费
//        discovery through getROCmInstallPath(), then consume the resolved
//        tree for real: version marker, archive magic, CMake package config,
//        public header; cross-check the on-disk deployment against the linked
//        library's runtime release.
//   HC-2 下游版本门禁决策流程
//        a downstream component gates on a minimum ROCm release, takes the
//        accept/reject branches, emits the diagnostic banner, writes a
//        decision record and reads it back.
//   HC-3 安装根重定位流程
//        relocate the deployment root, confirm the API follows the new root,
//        read the relocated marker, then switch back and confirm the original
//        tree is authoritative again (no stale resolution).
//
// Only built for the OHOS target: test_package/CMakeLists.txt gates the
// target behind ROCM_CORE_TEST_OHOS (set by test_package/conanfile.py when
// settings.os == "OHOS"), and the #error below makes the OHOS-only contract
// explicit at compile time.

#ifndef __OHOS__
#error "test_rocm_core_ohos.cpp must be compiled for HarmonyOS (OHOS target)"
#endif

#include <rocm_version.h>
#include <rocm_getpath.h>

#include <cerrno>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include <sys/stat.h>
#include <sys/types.h>

namespace {

int g_checks = 0;
int g_failed = 0;

void check(bool condition, const char* what) {
    ++g_checks;
    if (condition) {
        std::printf("    ok: %s\n", what);
    } else {
        ++g_failed;
        std::fprintf(stderr, "    FAIL: %s\n", what);
    }
}

std::string path_join(const std::string& dir, const std::string& name) {
    if (dir.empty()) {
        return name;
    }
    if (dir[dir.size() - 1] == '/') {
        return dir + name;
    }
    return dir + "/" + name;
}

std::string strip_trailing_slash(std::string path) {
    while (!path.empty() && path[path.size() - 1] == '/') {
        path.erase(path.size() - 1);
    }
    return path;
}

std::string trim_whitespace(std::string text) {
    while (!text.empty()) {
        const char last = text[text.size() - 1];
        if (last != '\n' && last != '\r' && last != ' ' && last != '\t') {
            break;
        }
        text.erase(text.size() - 1);
    }
    return text;
}

bool is_dir(const std::string& path) {
    struct stat info;
    return ::stat(path.c_str(), &info) == 0 && S_ISDIR(info.st_mode);
}

bool ensure_dir(const std::string& path) {
    if (path.empty()) {
        return false;
    }
    if (is_dir(path)) {
        return true;
    }
    const std::string::size_type slash = path.find_last_of('/');
    if (slash != std::string::npos && slash > 0) {
        if (!ensure_dir(path.substr(0, slash))) {
            return false;
        }
    }
    if (::mkdir(path.c_str(), 0755) == 0) {
        return true;
    }
    return errno == EEXIST && is_dir(path);
}

bool read_file(const std::string& path, std::string& out) {
    FILE* handle = std::fopen(path.c_str(), "rb");
    if (handle == nullptr) {
        return false;
    }
    char buffer[4096];
    const std::size_t count = std::fread(buffer, 1, sizeof(buffer), handle);
    std::fclose(handle);
    out.assign(buffer, count);
    return true;
}

bool read_prefix(const std::string& path, std::string& out, std::size_t count) {
    FILE* handle = std::fopen(path.c_str(), "rb");
    if (handle == nullptr) {
        return false;
    }
    std::vector<char> buffer(count, '\0');
    const std::size_t got = std::fread(buffer.data(), 1, count, handle);
    std::fclose(handle);
    out.assign(buffer.data(), got);
    return true;
}

bool write_file(const std::string& path, const std::string& content) {
    FILE* handle = std::fopen(path.c_str(), "wb");
    if (handle == nullptr) {
        return false;
    }
    const std::size_t written = std::fwrite(content.data(), 1, content.size(), handle);
    std::fclose(handle);
    return written == content.size();
}

bool contains(const std::string& haystack, const char* needle) {
    return haystack.find(needle) != std::string::npos;
}

struct Version {
    unsigned int major;
    unsigned int minor;
    unsigned int patch;
};

Version query_version() {
    Version value = {0, 0, 0};
    const VerErrors status = getROCmVersion(&value.major, &value.minor, &value.patch);
    if (status != VerSuccess) {
        value.major = 0xFFFFFFFFu;
        value.minor = 0xFFFFFFFFu;
        value.patch = 0xFFFFFFFFu;
    }
    return value;
}

std::string format_version(const Version& value) {
    char buffer[64];
    std::snprintf(buffer, sizeof(buffer), "%u.%u.%u", value.major, value.minor, value.patch);
    return std::string(buffer);
}

bool at_least(const Version& installed, unsigned int major, unsigned int minor, unsigned int patch) {
    if (installed.major != major) {
        return installed.major > major;
    }
    if (installed.minor != minor) {
        return installed.minor > minor;
    }
    return installed.patch >= patch;
}

// ── HC-1: installation discovery -> real artifact consumption ─────────────

int hc1_installation_discovery_and_artifact_consumption(const std::string& install_prefix,
                                                        const std::string& /*workdir*/) {
    check(is_dir(install_prefix),
          "HC-1 deployment prefix exists (given by the package manager)");
    check(::setenv("ROCM_PATH", install_prefix.c_str(), 1) == 0,
          "HC-1 deployment environment: ROCM_PATH points at the OHOS deployment prefix");

    char* install_path = nullptr;
    unsigned int length = 0;
    const PathErrors_t status = getROCmInstallPath(&install_path, &length);
    check(status == PathSuccess, "HC-1 getROCmInstallPath() resolves the installed tree");

    std::string root;
    if (install_path != nullptr) {
        root.assign(install_path);
        std::free(install_path);
    }
    check(!root.empty(), "HC-1 the resolved install root is non-empty");
    if (root.empty()) {
        return 1;
    }
    std::printf("      resolved install root: %s\n", root.c_str());
    check(strip_trailing_slash(root) == strip_trailing_slash(install_prefix),
          "HC-1 the resolved root is the OHOS deployment prefix (not a hard-coded default)");

    std::string marker;
    check(read_file(path_join(root, ".info/version"), marker),
          "HC-1 read <root>/.info/version from the resolved tree");
    check(trim_whitespace(marker) == "7.2.4",
          "HC-1 the deployment marker reports release 7.2.4");

    std::string magic;
    check(read_prefix(path_join(root, "lib/librocm-core.a"), magic, 8),
          "HC-1 open <root>/lib/librocm-core.a");
    check(magic == "!<arch>\n", "HC-1 the archive is a valid ar archive (magic !<arch>)");

    std::string cmake_config;
    check(read_file(path_join(root, "lib/cmake/rocm-core/rocm-core-config.cmake"), cmake_config),
          "HC-1 read <root>/lib/cmake/rocm-core/rocm-core-config.cmake");
    check(contains(cmake_config, "rocm"),
          "HC-1 the CMake package config is a real rocm-core config");

    std::string header;
    check(read_file(path_join(root, "include/rocm-core/rocm_version.h"), header),
          "HC-1 read <root>/include/rocm-core/rocm_version.h");
    check(contains(header, "getROCmVersion"),
          "HC-1 the public header declares getROCmVersion");

    const Version runtime = query_version();
    check(format_version(runtime) == trim_whitespace(marker),
          "HC-1 runtime release == deployment marker (no deployment drift)");

    return 0;
}

// ── HC-2: downstream version gate -> decision record ──────────────────────

int hc2_downstream_version_gate(const std::string& /*install_prefix*/,
                                const std::string& workdir) {
    const Version installed = query_version();
    const std::string installed_text = format_version(installed);
    check(installed.major != 0xFFFFFFFFu,
          "HC-2 downstream component queries the ROCm release (getROCmVersion)");

    struct Gate {
        unsigned int major;
        unsigned int minor;
        unsigned int patch;
        bool expected_accept;
        const char* label;
    };
    const Gate gates[] = {
        {7, 2, 0, true, "HC-2 gate >= 7.2.0 accepts the 7.2.4 deployment"},
        {7, 2, 4, true, "HC-2 gate >= 7.2.4 accepts the exact release"},
        {7, 3, 0, false, "HC-2 gate >= 7.3.0 rejects the older deployment"},
        {8, 0, 0, false, "HC-2 gate >= 8.0.0 rejects the older major"},
    };
    for (std::size_t i = 0; i < sizeof(gates) / sizeof(gates[0]); ++i) {
        const Gate& gate = gates[i];
        const bool accepted = at_least(installed, gate.major, gate.minor, gate.patch);
        check(accepted == gate.expected_accept, gate.label);
        std::printf("      decision %s: installed %s vs required >= %u.%u.%u\n",
                    accepted ? "GO" : "NO-GO", installed_text.c_str(),
                    gate.major, gate.minor, gate.patch);
    }

    if (at_least(installed, 7, 2, 0)) {
        check(printBuildInfo() == VerSuccess,
              "HC-2 accepted branch emits the build-info banner (printBuildInfo)");
        check(std::strncmp(ROCM_BUILD_INFO, "7.2.4", 5) == 0,
              "HC-2 the banner carries the release prefix");
    }

    const std::string report_path = path_join(workdir, "compat-report.txt");
    std::string report;
    report += "installed=" + installed_text + "\n";
    report += std::string("gate=>=7.2.0:") + (at_least(installed, 7, 2, 0) ? "GO" : "NO-GO") + "\n";
    report += "build_info=" + std::string(ROCM_BUILD_INFO) + "\n";
    check(write_file(report_path, report),
          "HC-2 write the compatibility decision record");
    std::string report_back;
    check(read_file(report_path, report_back),
          "HC-2 read the decision record back");
    check(contains(report_back, ("installed=" + installed_text).c_str()),
          "HC-2 the decision record carries the installed release");

    return 0;
}

// ── HC-3: installation-root relocation -> no stale resolution ─────────────

int hc3_installation_root_relocation(const std::string& install_prefix,
                                     const std::string& workdir) {
    const std::string relocated = path_join(workdir, "relocated-rocm");
    check(ensure_dir(path_join(relocated, ".info")),
          "HC-3 deploy a relocated installation tree");
    check(ensure_dir(path_join(relocated, "lib")),
          "HC-3 the relocated tree has lib/");
    check(write_file(path_join(relocated, ".info/version"), "9.9.9-relocated-probe\n"),
          "HC-3 the relocated tree carries its own version marker");

    check(::setenv("ROCM_PATH", relocated.c_str(), 1) == 0,
          "HC-3 point ROCM_PATH at the relocated deployment");
    char* install_path = nullptr;
    unsigned int length = 0;
    check(getROCmInstallPath(&install_path, &length) == PathSuccess,
          "HC-3 getROCmInstallPath() follows the relocation");
    std::string relocated_root;
    if (install_path != nullptr) {
        relocated_root.assign(install_path);
        std::free(install_path);
    }
    if (!relocated_root.empty()) {
        std::printf("      relocated root: %s\n", relocated_root.c_str());
        std::string marker;
        check(read_file(path_join(relocated_root, ".info/version"), marker),
              "HC-3 read the marker from the relocated tree");
        check(trim_whitespace(marker) == "9.9.9-relocated-probe",
              "HC-3 the relocation took effect (the new marker is visible)");
    }

    check(::setenv("ROCM_PATH", install_prefix.c_str(), 1) == 0,
          "HC-3 switch ROCM_PATH back to the original deployment");
    char* path_back = nullptr;
    unsigned int length_back = 0;
    check(getROCmInstallPath(&path_back, &length_back) == PathSuccess,
          "HC-3 getROCmInstallPath() re-resolves the original tree");
    std::string original_root;
    if (path_back != nullptr) {
        original_root.assign(path_back);
        std::free(path_back);
    }
    if (!original_root.empty()) {
        std::string marker;
        check(read_file(path_join(original_root, ".info/version"), marker),
              "HC-3 read the original marker after switching back");
        check(trim_whitespace(marker) == "7.2.4",
              "HC-3 the original tree is authoritative again (no stale resolution)");
    }

    return 0;
}

int run_case(const char* id, const char* title,
             int (*fn)(const std::string&, const std::string&),
             const std::string& install_prefix, const std::string& workdir) {
    std::printf("\n[%s] %s\n", id, title);
    const int failures_before = g_failed;
    fn(install_prefix, workdir);
    if (g_failed == failures_before) {
        std::printf("[%s] PASS\n", id);
        return 0;
    }
    std::printf("[%s] FAIL\n", id);
    return 1;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 3) {
        std::fprintf(stderr,
                     "usage: %s <installed-prefix> <workdir>\n"
                     "  installed-prefix: the deployed rocm-core package prefix\n"
                     "  workdir:          writable directory for reports/relocation\n",
                     argv[0]);
        return 2;
    }
    const std::string install_prefix = argv[1];
    const std::string workdir = argv[2];
    if (!ensure_dir(workdir)) {
        std::fprintf(stderr, "cannot create workdir: %s\n", workdir.c_str());
        return 2;
    }

    std::printf("== rocm-core OHOS complete consumer flows (rule 12) ==\n");
    std::printf("   target : HarmonyOS (__OHOS__)\n");
    std::printf("   prefix : %s\n", install_prefix.c_str());
    std::printf("   workdir: %s\n", workdir.c_str());

    int passed = 0;
    passed += (run_case("HC-1", "安装树发现与真实产物消费 (discovery -> real artifact consumption)",
                        hc1_installation_discovery_and_artifact_consumption,
                        install_prefix, workdir) == 0);
    passed += (run_case("HC-2", "下游版本门禁决策流程 (version gate -> decision record)",
                        hc2_downstream_version_gate,
                        install_prefix, workdir) == 0);
    passed += (run_case("HC-3", "安装根重定位流程 (relocation -> no stale resolution)",
                        hc3_installation_root_relocation,
                        install_prefix, workdir) == 0);

    std::printf("\n== complete consumer flows: %d/3 cases passed (%d checks, %d failed) ==\n",
                passed, g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
