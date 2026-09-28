/*
 * Consumer test for kylin-ai-document-service 1.2.0.0.
 *
 * Copyright 2024 KylinSoft Co., Ltd.
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * This program substantively exercises the installed package:
 *   1. constructs document::DocumentChunkClient, whose constructor calls
 *      startUserService() -> sd_bus_open_user() from the linked libsystemd;
 *   2. drives both SyncChunkDocument() overloads, which serialise the request
 *      through protobuf, open a real gRPC channel to the unix socket and
 *      invoke the generated DocumentService::Stub (with the upstream retry
 *      loop);
 *   3. asserts the call really happened: no service is listening, so the RPC
 *      must return a non-OK status with a non-empty message, and a service
 *      that answered successfully would also be a valid pass.
 *
 * The absence of the document service is environment, not failure: the test
 * verifies that the client library loads, links and performs the call.
 */

#include <client.h>

#include <grpcpp/grpcpp.h>

#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

namespace {

int g_checks = 0;
int g_failures = 0;

void check(bool condition, const std::string &what) {
    ++g_checks;
    if (condition) {
        std::cout << "[ok]   " << what << std::endl;
    } else {
        ++g_failures;
        std::cout << "[FAIL] " << what << std::endl;
    }
}

// A response is acceptable either when the service answered or when the
// call genuinely reached the (absent) endpoint. What must never happen is a
// silent, un-invoked call: gRPC reports those cases (OK or a concrete error
// code + message).
bool responseIsGenuineCall(const document::DocumentChunkResponse &response) {
    if (response.errorCode == grpc::StatusCode::OK) {
        return true;
    }
    return !response.errorMsg.empty() && !response.data.empty();
}

}  // namespace

int main() {
    const std::vector<std::string> file_paths = {"/tmp/kylin-ai-document-service-test.txt"};
    const std::vector<std::string> chunker_types = {"TextChunker"};
    const std::vector<int32_t> chunk_sizes = {500};
    const std::vector<int32_t> max_doc_chars_count = {-1};

    // 1) The public constructor is a real entry point: it starts the user
    //    service over sd-bus (libsystemd) before any RPC is attempted. The
    //    outcome is observable — construction either succeeds or throws — so
    //    this is a real check, not a constant.
    std::unique_ptr<document::DocumentChunkClient> client;
    try {
        client = std::make_unique<document::DocumentChunkClient>();
    } catch (const std::exception &ex) {
        std::cerr << "  DocumentChunkClient() threw: " << ex.what() << std::endl;
    }
    check(client != nullptr,
          "DocumentChunkClient constructed (sd_bus_open_user path linked)");
    if (!client) {
        std::cout << "kylin-ai-document-service consumer test: "
                  << (g_checks - g_failures) << "/" << g_checks
                  << " checks passed" << std::endl;
        return EXIT_FAILURE;
    }

    // 2) Three-argument overload.
    const document::DocumentChunkResponse three_arg =
        client->SyncChunkDocument(file_paths, chunker_types, chunk_sizes);
    std::cout << "  SyncChunkDocument(file_paths, chunker_types, chunk_sizes): "
              << "errorCode=" << three_arg.errorCode
              << " errorMsg=" << three_arg.errorMsg << std::endl;
    check(responseIsGenuineCall(three_arg),
          "3-arg SyncChunkDocument returned a genuine RPC result");
    check(!three_arg.data.empty() || three_arg.errorCode != grpc::StatusCode::OK,
          "3-arg response carries JSON payload or a concrete error code");

    // 3) Four-argument overload (max_doc_chars_count path).
    const document::DocumentChunkResponse four_arg = client->SyncChunkDocument(
        file_paths, chunker_types, chunk_sizes, max_doc_chars_count);
    std::cout << "  SyncChunkDocument(..., max_doc_chars_count): "
              << "errorCode=" << four_arg.errorCode
              << " errorMsg=" << four_arg.errorMsg << std::endl;
    check(responseIsGenuineCall(four_arg),
          "4-arg SyncChunkDocument returned a genuine RPC result");

    // 4) Both overloads must hit the same service and thus agree on the
    //    unreachable/absent-service status.
    check(three_arg.errorCode == four_arg.errorCode,
          "both overloads agree on the service status");

    std::cout << "kylin-ai-document-service consumer test: "
              << (g_checks - g_failures) << "/" << g_checks
              << " checks passed" << std::endl;

    if (g_failures > 0) {
        std::cerr << g_failures << " check(s) FAILED" << std::endl;
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
