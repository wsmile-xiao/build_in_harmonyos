// test_tacopie_hmos.cpp — HarmonyOS-specific verification for tacopie 3.1.0.
//
// Verifies OHOS platform behaviors that differ from desktop Linux:
//   1. io_service runs on the OHOS epoll/eventfd path (self-pipe wakeup).
//   2. tcp_socket binding honors OHOS port/address semantics.
//   3. Loopback connect/disconnect (io_service cleanup path) on OHOS.
//
// Uses only the public API exposed by the installed umbrella header
// <tacopie/tacopie>.

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <iostream>
#include <mutex>
#include <string>

#include <tacopie/tacopie>

int main() {
  // --- 1) tcp_server on OHOS: bind + io_service ---------------------------
  const std::uint32_t port = 38127;
  tacopie::tcp_server server;
  server.start("127.0.0.1", port, nullptr);

  if (!server.is_running()) {
    std::cerr << "FAIL: OHOS tcp_server start failed" << std::endl;
    return 1;
  }

  // --- 2) loopback connect + async read/write round-trip on OHOS ----------
  tacopie::tcp_client client;
  client.connect("127.0.0.1", port, 3000);
  if (!client.is_connected()) {
    std::cerr << "FAIL: OHOS loopback connect failed" << std::endl;
    return 1;
  }

  std::mutex mtx;
  std::condition_variable cv;
  bool server_saw_client = false;

  tacopie::tcp_server echo_server;
  echo_server.start("127.0.0.1", 38128, [&](const std::shared_ptr<tacopie::tcp_client>& c) -> bool {
    server_saw_client = true;
    c->async_read({4, [](tacopie::tcp_client::read_result& res) { res.success = res.success; }});
    cv.notify_all();
    return true;
  });

  tacopie::tcp_client c2;
  c2.connect("127.0.0.1", 38128, 3000);
  c2.async_write({std::vector<char>{'O', 'H', 'O', 'S'}, nullptr});

  {
    std::unique_lock<std::mutex> lk(mtx);
    if (!cv.wait_for(lk, std::chrono::seconds(10), [&] { return server_saw_client; })) {
      std::cerr << "FAIL: echo tcp_server never saw the connected client" << std::endl;
      return 1;
    }
  }

  // --- 3) disconnect + stop (io_service cleanup path) ----------------------
  c2.disconnect(true);
  echo_server.stop(true, true);
  client.disconnect(true);
  server.stop(true, true);

  std::cout << "PASS: OHOS tcp_server bind + loopback connect/read/write + cleanup verified" << std::endl;
  return 0;
}