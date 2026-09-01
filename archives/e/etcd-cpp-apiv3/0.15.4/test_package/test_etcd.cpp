// HarmonyOS PC consumer smoke test for etcd-cpp-apiv3 0.15.4 (core-only
// synchronous runtime).
//
// R34: the test must exercise the packaged API for real. It constructs an
// etcd::SyncClient and calls put()/get()/head(), driving the full link
// (public API -> protobuf serialization -> gRPC channel -> response
// parsing). No etcd server exists in the build environment, so the calls
// are expected to fail with the gRPC UNAVAILABLE (14) status — connection
// refused on the loopback endpoint maps deterministically to that code —
// instead of crashing or hanging: that is the documented error path of the
// library (SyncClient uses lazy gRPC channels; ParseResponse maps a bad
// grpc::Status onto Response::error_code() without throwing). A crash, a
// hang, a missing symbol, or an unexpected status fails the test; graceful
// transport-error handling passes it.

#include <etcd/SyncClient.hpp>
#include <etcd/Response.hpp>
#include <etcd/Value.hpp>

#include <grpcpp/support/status.h>

#include <cstdio>
#include <string>

static int failures = 0;

static void check(bool cond, const char* what) {
  if (!cond) {
    std::fprintf(stderr, "test_etcd: FAILED: %s\n", what);
    ++failures;
  } else {
    std::printf("test_etcd: ok: %s\n", what);
  }
}

// Without a server every call must surface the transport failure instead
// of crashing: gRPC status UNAVAILABLE (14) plus a non-empty message.
static void check_unavailable(const etcd::Response& resp, const char* op) {
  check(resp.error_code() == grpc::StatusCode::UNAVAILABLE,
        "transport error is UNAVAILABLE(14)");
  check(!resp.error_message().empty(), "error message is non-empty");
  std::printf("test_etcd: %s error: code=%d msg=%s\n",
              op, resp.error_code(), resp.error_message().c_str());
}

int main() {
  // 1. Client construction (lazy gRPC channel; no server contacted yet).
  etcd::SyncClient client("http://127.0.0.1:2379");

  // 2. put(): exercises protobuf serialization + the async gRPC call +
  //    response parsing of the KV service. On success the round-trip is
  //    verified by get() below.
  etcd::Response put_resp = client.put("/harmonyos/test", "hello_from_test");
  if (put_resp.is_ok()) {
    std::printf("test_etcd: put ok (live server)\n");
  } else {
    check_unavailable(put_resp, "put");
  }

  // 3. get(): exercises the Range request path.
  etcd::Response get_resp = client.get("/harmonyos/test");
  if (get_resp.is_ok()) {
    check(get_resp.value().as_string() == "hello_from_test",
          "get round-trips the stored value");
  } else {
    check_unavailable(get_resp, "get");
  }

  // 4. head(): exercises the status endpoint path.
  etcd::Response head_resp = client.head();
  if (head_resp.is_ok()) {
    check(head_resp.cluster_id() != 0, "head reports a cluster id");
  } else {
    check_unavailable(head_resp, "head");
  }

  if (failures > 0) {
    std::fprintf(stderr, "test_etcd: %d check(s) failed\n", failures);
    return 1;
  }
  std::printf("test_etcd: OK\n");
  return 0;
}
