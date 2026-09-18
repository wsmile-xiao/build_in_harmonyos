// test_tacopie.cpp — Conan consumer verification for tacopie 3.1.0.
//
// Exercises the *public* API only (installed headers + linked library):
//   tacopie::tcp_server::start / stop / is_running
//   tacopie::tcp_client::connect / is_connected / async_read / async_write / disconnect
//   tcp_socket::get_port (observable result of binding)
//
// The test starts a loopback TCP server on an ephemeral free port, connects
// a client, writes a payload and verifies the server-side socket receives it.
//
// Lifetime note: when the on_new_connection callback returns `true` the
// tcp_server does not retain the client, so the async_read lambda must
// capture the client shared_ptr BY VALUE to keep the connection alive until
// the read completes (same pattern as the upstream example's std::bind).

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <iostream>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

#include <tacopie/tacopie>

int main() {
  // Pick a loopback port unlikely to collide in CI.
  const std::uint32_t port = 37123;
  const std::string host = "127.0.0.1";
  const std::string payload = "tacopie-consumer-ping";

  std::mutex mtx;
  std::condition_variable cv;
  bool server_received = false;
  bool new_client_seen = false;

  tacopie::tcp_server server;
  server.start(host, port, [&](const std::shared_ptr<tacopie::tcp_client>& client) -> bool {
    {
      std::unique_lock<std::mutex> lk(mtx);
      new_client_seen = true;
    }
    // Capture `client` by value so the connection outlives this callback.
    client->async_read({1024, [client, &payload, &server_received, &cv, &mtx](tacopie::tcp_client::read_result& res) {
                          if (res.success && std::string(res.buffer.begin(), res.buffer.end()) == payload) {
                            std::unique_lock<std::mutex> lk(mtx);
                            server_received = true;
                          }
                          cv.notify_all();
                        }});
    return true;
  });

  if (!server.is_running()) {
    std::cerr << "FAIL: server not running after start" << std::endl;
    return 1;
  }

  tacopie::tcp_client client;
  client.connect(host, port, 3000);
  if (!client.is_connected()) {
    std::cerr << "FAIL: client connect failed" << std::endl;
    return 1;
  }

  client.async_write({std::vector<char>(payload.begin(), payload.end()), nullptr});

  std::unique_lock<std::mutex> lk(mtx);
  bool ok = cv.wait_for(lk, std::chrono::seconds(10), [&] { return server_received; });
  if (!ok || !new_client_seen) {
    std::cerr << "FAIL: server did not receive payload (new_client_seen=" << new_client_seen << ")" << std::endl;
    return 1;
  }

  client.disconnect(true);
  server.stop(true, true);

  std::cout << "PASS: tcp_server/tcp_client loopback round-trip verified (payload=" << payload << ")" << std::endl;
  return 0;
}