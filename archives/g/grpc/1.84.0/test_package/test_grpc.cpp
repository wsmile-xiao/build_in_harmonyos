// gRPC 1.84.0 L1 consumer test for HarmonyOS PC (aarch64).
//
// Exercises the packaged library end to end, over a real connection:
//
//   1. grpc::Version()                     — link + runtime symbol resolution
//   2. a real gRPC server on 127.0.0.1:0   — grpc::ServerBuilder with an
//      AsyncGenericService (no .proto / protoc needed) and its own
//      completion queue; BuildAndStart + a draining thread
//   3. grpc::CreateChannel to that port    — resolver, TCP, HTTP/2 settings
//      exchange; the channel must reach GRPC_CHANNEL_READY.  WaitForConnected()
//      is used because a gRPC channel connects *lazily*: polling GetState(false)
//      alone leaves it in IDLE forever (that mistake made an earlier revision of
//      this test fail with "state=0").
//   4. negative control: 127.0.0.1:1       — must never report READY
//   5. clean teardown
//
// Two earlier revisions are deliberately not used here:
//   * a synchronous grpc::Server aborted its own BuildAndStart with
//     "E0000 server_builder.cc:469] At least one of the completion queues must
//     be frequently polled" - the sync server's private CQ cannot be drained
//     before the server object exists;
//   * a bare TCP listener can never produce READY, because READY means the
//     HTTP/2 handshake completed, which needs a real gRPC peer.

#include <grpcpp/grpcpp.h>
#include <grpcpp/generic/async_generic_service.h>  // grpc::AsyncGenericService

#include <chrono>
#include <cstdio>
#include <memory>
#include <string>
#include <thread>

namespace {

constexpr auto kConnectTimeout = std::chrono::seconds(20);

}  // namespace

int main() {
  // ── 1. Version symbol: the library linked and resolves at runtime ────────
  const std::string version = grpc::Version();
  if (version.empty()) {
    std::fprintf(stderr, "test_grpc: FAIL — grpc::Version() returned empty\n");
    return 1;
  }
  std::printf("grpc version: %s\n", version.c_str());

  // ── 2. A real gRPC server (async generic service, no generated stubs) ────
  grpc::ServerBuilder builder;
  int bound_port = 0;
  builder.AddListeningPort("127.0.0.1:0", grpc::InsecureServerCredentials(),
                           &bound_port);
  grpc::AsyncGenericService service;
  builder.RegisterAsyncGenericService(&service);
  std::unique_ptr<grpc::ServerCompletionQueue> cq = builder.AddCompletionQueue();
  std::unique_ptr<grpc::Server> server = builder.BuildAndStart();
  if (server == nullptr || bound_port == 0) {
    std::fprintf(stderr, "test_grpc: FAIL — BuildAndStart returned null (port=%d)\n",
                 bound_port);
    return 1;
  }
  std::printf("grpc server listening on 127.0.0.1:%d\n", bound_port);

  // Drain the completion queue for the lifetime of the server.
  std::thread cq_poller([&cq] {
    void *tag = nullptr;
    bool ok = false;
    while (cq->Next(&tag, &ok)) {
      // Nothing is requested through this queue in this test.
    }
  });

  // ── 3. Client channel must reach READY against that server ───────────────
  const std::string target = "127.0.0.1:" + std::to_string(bound_port);
  auto channel = grpc::CreateChannel(target, grpc::InsecureChannelCredentials());
  if (channel == nullptr) {
    std::fprintf(stderr, "test_grpc: FAIL — CreateChannel returned null\n");
    server->Shutdown();
    cq->Shutdown();
    cq_poller.join();
    return 1;
  }
  const bool connected = channel->WaitForConnected(
      std::chrono::system_clock::now() + kConnectTimeout);
  if (!connected) {
    std::fprintf(stderr,
                 "test_grpc: FAIL — channel to %s never became READY (state=%d)\n",
                 target.c_str(), static_cast<int>(channel->GetState(false)));
    server->Shutdown();
    cq->Shutdown();
    cq_poller.join();
    return 1;
  }
  std::printf("client channel to %s is READY (state=%d)\n", target.c_str(),
              static_cast<int>(channel->GetState(false)));

  // ── 4. Negative control: a dead endpoint must not be READY ───────────────
  auto dead = grpc::CreateChannel("127.0.0.1:1", grpc::InsecureChannelCredentials());
  if (dead == nullptr) {
    std::fprintf(stderr, "test_grpc: FAIL — CreateChannel(dead) returned null\n");
    server->Shutdown();
    cq->Shutdown();
    cq_poller.join();
    return 1;
  }
  if (dead->WaitForConnected(std::chrono::system_clock::now() +
                             std::chrono::seconds(2))) {
    std::fprintf(stderr, "test_grpc: FAIL — channel to dead port became READY\n");
    server->Shutdown();
    cq->Shutdown();
    cq_poller.join();
    return 1;
  }
  std::printf("negative control ok: dead endpoint is not READY (state=%d)\n",
              static_cast<int>(dead->GetState(false)));

  // ── 5. Teardown ─────────────────────────────────────────────────────────
  channel.reset();
  dead.reset();
  server->Shutdown();
  cq->Shutdown();
  cq_poller.join();
  std::printf("test_grpc: PASS — grpc 1.84.0 server + client transport OK\n");
  return 0;
}
