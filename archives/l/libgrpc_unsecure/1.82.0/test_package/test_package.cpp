// HarmonyOS PC consumer smoke test for libgrpc_unsecure 1.82.0.
// Exercises the TLS-free gRPC++ API surface: channel creation with
// InsecureChannelCredentials, completion queue, grpc::Version() runtime
// symbol, and the C-core grpc_version_string symbol (grpc_unsecure lib).

#include <grpcpp/grpcpp.h>
#include <grpcpp/channel.h>
#include <grpcpp/completion_queue.h>
#include <grpcpp/create_channel.h>

#include <grpc/grpc.h>

#include <cstdio>
#include <memory>
#include <string>

int main() {
  // Version symbols prove both the C++ binding (grpc++_unsecure) and the
  // C core (grpc_unsecure) linked and resolved at runtime.
  // Use explicit checks instead of assert(): assert() is compiled out under
  // NDEBUG (default Release), which would silently void the smoke test.
  const std::string version = grpc::Version();
  if (version.empty()) {
    std::fprintf(stderr, "test_package: FAILED, grpc::Version() returned empty\n");
    return 1;
  }
  std::printf("grpc version: %s\n", version.c_str());

  const char* c_version = grpc_version_string();
  if (c_version == nullptr || c_version[0] == '\0') {
    std::fprintf(stderr, "test_package: FAILED, grpc_version_string() empty\n");
    return 1;
  }
  std::printf("grpc core version: %s\n", c_version);

  // Create a channel to a local (non-running) endpoint; the call itself
  // exercises the insecure channel construction path without requiring a
  // server or TLS (this is the unsecure core's defining capability).
  auto channel = grpc::CreateChannel(
      "127.0.0.1:1", grpc::InsecureChannelCredentials());
  if (channel == nullptr) {
    std::fprintf(stderr, "test_package: FAILED, CreateChannel returned null\n");
    return 1;
  }

  // A completion queue exercises the gpr sync layer used throughout grpc++.
  auto cq = std::make_unique<grpc::CompletionQueue>();
  if (cq == nullptr) {
    std::fprintf(stderr, "test_package: FAILED, CompletionQueue is null\n");
    return 1;
  }
  cq->Shutdown();

  std::printf("test_package: OK\n");
  return 0;
}
