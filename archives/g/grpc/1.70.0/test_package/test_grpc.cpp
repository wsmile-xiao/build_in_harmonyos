// HarmonyOS PC consumer smoke test for grpc 1.70.0.
// Exercises the gRPC++ API surface that buildbox-common/recc rely on:
// channel creation, completion queue, and the grpc::Version() runtime symbol.

#include <grpcpp/grpcpp.h>
#include <grpcpp/channel.h>
#include <grpcpp/completion_queue.h>
#include <grpcpp/create_channel.h>

#include <cstdio>
#include <memory>
#include <string>

int main() {
  // Version symbol proves the grpc++ library linked and resolved at runtime.
  // Use explicit checks instead of assert(): assert() is compiled out under
  // NDEBUG (default Release), which would silently void the smoke test.
  const std::string version = grpc::Version();
  if (version.empty()) {
    std::fprintf(stderr, "test_grpc: FAILED, grpc::Version() returned empty\n");
    return 1;
  }
  std::printf("grpc version: %s\n", version.c_str());

  // Create a channel to a local (non-running) endpoint; the call itself
  // exercises the channel construction path without requiring a server.
  auto channel = grpc::CreateChannel(
      "127.0.0.1:1", grpc::InsecureChannelCredentials());
  if (channel == nullptr) {
    std::fprintf(stderr, "test_grpc: FAILED, CreateChannel returned null\n");
    return 1;
  }

  // A completion queue exercises the gpr sync layer used throughout grpc++.
  auto cq = std::make_unique<grpc::CompletionQueue>();
  if (cq == nullptr) {
    std::fprintf(stderr, "test_grpc: FAILED, CompletionQueue is null\n");
    return 1;
  }

  std::printf("test_grpc: OK\n");
  return 0;
}
