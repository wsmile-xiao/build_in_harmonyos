// Consumer test for kylin-ai-proto (INTERFACE data package).
//
// The package ships protocol definition files (gdbus XML + grpc proto) that
// downstream code-generation consumers read at build time, and the CMake
// package config files (KylinAiProtoConfig.cmake / Targets / Functions /
// Generate) that consumers load via find_package(KylinAiProto). There is no
// runtime library.  This test therefore verifies the three things the package
// actually guarantees:
//   1. find_package(KylinAiProto) resolves and KylinAiProto::KylinAiProto
//      links (the build would fail otherwise).
//   2. The installed protocol files exist, are non-empty and carry the
//      expected content.
//   3. The installed CMake package config files exist and are non-empty
//      (they are the package's build-time deliverable; this also makes the
//      consumer test genuinely depend on the package's lib/ artifacts, so
//      the CI L1e destructive negative test can verify it).
#include <cstdio>
#include <fstream>
#include <iterator>
#include <string>

namespace {

int check_file(const std::string& path, const std::string& needle) {
    std::ifstream in(path, std::ios::binary);
    if (!in.is_open()) {
        std::fprintf(stderr, "kylin-ai-proto: cannot open '%s'\n", path.c_str());
        return 1;
    }
    std::string content((std::istreambuf_iterator<char>(in)),
                        std::istreambuf_iterator<char>());
    if (content.empty()) {
        std::fprintf(stderr, "kylin-ai-proto: '%s' is empty\n", path.c_str());
        return 1;
    }
    if (needle.empty()) {
        return 0;
    }
    if (content.find(needle) == std::string::npos) {
        std::fprintf(stderr, "kylin-ai-proto: expected '%s' not found in '%s'\n",
                     needle.c_str(), path.c_str());
        return 1;
    }
    return 0;
}

}  // namespace

int main() {
    const std::string base = KAP_PROTOCOLS_DIR;
    const std::string cmake_dir = KAP_CMAKE_DIR;

    // gdbus XML introspection file: gennlpservice.xml must declare a <node>.
    if (check_file(base + "/gdbus/gennlpservice.xml", "<node") != 0) return 1;
    // grpc proto: milvus.proto must declare a proto3 package.
    if (check_file(base + "/grpc/vector-db/milvus.proto", "package ") != 0) return 1;
    // CMake package config deliverables (consumed by find_package at build
    // time by every downstream project; KylinAiProtoConfig.cmake.in must be
    // configured, so check the generated Config and the copied Functions /
    // Generate helpers are present).
    if (check_file(cmake_dir + "/KylinAiProtoConfig.cmake", "KylinAiProto") != 0) return 1;
    if (check_file(cmake_dir + "/KylinAiProtoConfigVersion.cmake", "PACKAGE_VERSION") != 0) return 1;
    if (check_file(cmake_dir + "/KylinAiProtoTargets.cmake", "KylinAiProto") != 0) return 1;
    if (check_file(cmake_dir + "/KylinAiProtoFunctions.cmake", "kylin_ai") != 0) return 1;
    if (check_file(cmake_dir + "/KylinAiProtoGenerate.cmake", "kylin_ai") != 0) return 1;

    std::printf("test kylin-ai-proto 1.0.0.1: OK\n");
    return 0;
}
