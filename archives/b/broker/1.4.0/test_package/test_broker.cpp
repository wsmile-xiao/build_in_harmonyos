// Consumer test suite for broker 1.4.0 on HarmonyOS PC.
//
// Single binary with one subcommand per test case (registered as separate
// CTest cases in CMakeLists.txt). Every case exercises the *installed*
// libbroker through its public headers only.
//
// Important: the upstream 22 CTest suites run over CAF's *fake* network
// (test_multiplexer, see tests/cpp/integration.cc), so they never exercise
// the real TCP transport. These consumer cases therefore peer two real
// endpoints over 127.0.0.1 loopback and validate actual socket I/O on OHOS.
//
// Test inventory (assertion counts printed at runtime; keep in sync with
// MANIFEST.yml):
//   version     - endpoint lifecycle + topic serialization                     (2)
//   roundtrip   - loopback peering pub-sub roundtrip of several data types     (12)
//   filter      - topic-prefix subscription filtering across peers (pos/neg)   (4)
//   burst       - 1000-message burst delivered in order over loopback          (3)
//   store       - master store (memory backend) put/get/exists/erase           (7)
//   peer_error  - error path: peering to a closed localhost port fails fast    (1)
//   status      - status_subscriber idle state (variant holds broker::none)    (1)
//
// Assertion helpers count via a counter printed at exit; a nonzero return
// code marks the case as failed.
#include <broker/broker.hh>

#include <chrono>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

namespace {

int checks = 0;
int failures = 0;

void check(bool cond, const char* what) {
  ++checks;
  if (!cond) {
    ++failures;
    std::cerr << "FAIL: " << what << std::endl;
  }
}

// A listening endpoint plus a connector endpoint peered to it over real
// loopback TCP. The listener subscribes before the peering is established,
// so subscription filters are part of the peering handshake.
struct peer_pair {
  broker::endpoint listener;
  broker::endpoint connector;
  uint16_t port = 0;

  peer_pair() {
    port = listener.listen("127.0.0.1", 0);
  }

  bool connect(broker::timeout::seconds retry = broker::timeout::seconds(1)) {
    return connector.peer("127.0.0.1", port, retry);
  }
};

int test_version() {
  broker::endpoint ep;
  check(!broker::to_string(broker::topic{"/a/b"}).empty(), "topic serializes");
  check(ep.is_shutdown() == false, "fresh endpoint not shutdown");
  ep.shutdown();
  return failures == 0 ? 0 : 1;
}

int test_roundtrip() {
  peer_pair pp;
  broker::topic t{"/rt/all"};
  auto sub = pp.listener.make_subscriber({t});
  check(pp.connect(), "loopback peering established");
  // Count (uint64).
  pp.connector.publish(t, broker::data{broker::count{42}});
  auto msg = sub.get(std::chrono::seconds(10));
  check(static_cast<bool>(msg), "count message received");
  if (msg) {
    check(broker::get_topic(*msg) == t, "received topic matches");
    auto d = broker::get_data(*msg);
    check(caf::holds_alternative<broker::count>(d.get_data()),
          "count type preserved");
    if (caf::holds_alternative<broker::count>(d.get_data()))
      check(caf::get<broker::count>(d.get_data()) == 42u,
            "count value preserved");
  }
  // String.
  {
    auto pub = pp.connector.make_publisher(t);
    pub.publish(broker::data{std::string("hello")});
    msg = sub.get(std::chrono::seconds(10));
    check(static_cast<bool>(msg), "string message received");
    if (msg) {
      auto d = broker::get_data(*msg);
      check(caf::holds_alternative<std::string>(d.get_data()),
            "string type preserved");
      if (caf::holds_alternative<std::string>(d.get_data()))
        check(caf::get<std::string>(d.get_data()) == "hello",
              "string value preserved");
    }
  }
  // Table.
  {
    broker::table tab;
    tab.emplace(broker::data{std::string("k")},
                broker::data{broker::count{7}});
    pp.connector.publish(t, broker::data{tab});
    msg = sub.get(std::chrono::seconds(10));
    check(static_cast<bool>(msg), "table message received");
    if (msg) {
      auto d = broker::get_data(*msg);
      check(caf::holds_alternative<broker::table>(d.get_data()),
            "table type preserved");
      if (caf::holds_alternative<broker::table>(d.get_data())) {
        auto& rt = caf::get<broker::table>(d.get_data());
        auto it = rt.find(broker::data{std::string("k")});
        check(it != rt.end(), "table key present after roundtrip");
        if (it != rt.end())
          check(caf::get<broker::count>(it->second.get_data()) == 7u,
                "table value preserved");
      }
    }
  }
  pp.listener.shutdown();
  pp.connector.shutdown();
  return failures == 0 ? 0 : 1;
}

int test_filter() {
  peer_pair pp;
  broker::topic exact{"/ft/exact"};
  auto sub = pp.listener.make_subscriber({exact});
  check(pp.connect(), "loopback peering established");
  // Non-matching topic must not be delivered.
  pp.connector.publish(broker::topic{"/ft/other"},
                       broker::data{broker::count{2}});
  auto msg = sub.get(std::chrono::milliseconds(500));
  check(!msg, "no delivery for non-matching topic");
  // Matching publish is delivered.
  pp.connector.publish(exact, broker::data{broker::count{3}});
  msg = sub.get(std::chrono::seconds(10));
  check(static_cast<bool>(msg), "matching publish delivered");
  if (msg)
    check(broker::get_topic(*msg) == exact, "matching topic received");
  pp.listener.shutdown();
  pp.connector.shutdown();
  return failures == 0 ? 0 : 1;
}

int test_burst(broker::count total = 1000) {
  peer_pair pp;
  broker::topic t{"/burst"};
  // Subscriber credit (max_qsize) covers a batch window.
  auto sub = pp.listener.make_subscriber({t}, 200);
  check(pp.connect(), "loopback peering established");
  // broker::publisher::publish enforces upstream backpressure: the in-flight
  // window is bounded by the stream credit chain, so we publish in batches of
  // 10 and drain each batch before the next. 1000 messages still traverse the
  // real loopback transport and are verified for volume and order.
  auto pub = pp.connector.make_publisher(t);
  constexpr broker::count batch = 10;
  broker::count seen = 0;
  bool ordered = true;
  for (broker::count i = 0; i < total; i += batch) {
    for (broker::count j = 0; j < batch; ++j)
      pub.publish(broker::data{i + j});
    auto xs = sub.get(batch, std::chrono::seconds(15));
    if (xs.size() != batch) {
      seen += static_cast<broker::count>(xs.size());
      break;
    }
    for (auto& m : xs) {
      auto d = broker::get_data(m);
      if (!caf::holds_alternative<broker::count>(d.get_data()) ||
          caf::get<broker::count>(d.get_data()) != seen)
        ordered = false;
      ++seen;
    }
  }
  check(seen == total, "all burst messages received");
  check(ordered, "burst messages in order");
  pp.listener.shutdown();
  pp.connector.shutdown();
  return failures == 0 ? 0 : 1;
}

int test_store() {
  broker::endpoint ep;
  auto res = ep.attach_master("consumer-store", broker::backend::memory);
  check(static_cast<bool>(res), "attach_master succeeds");
  if (!res)
    return 1;
  broker::store m = *res;
  check(m.name() == "consumer-store", "store name preserved");
  broker::data key{std::string("alpha")};
  broker::data val{broker::count{99}};
  // put/erase are fire-and-forget on the store actor; verify effects via
  // exists/get which await the store's response.
  m.put(key, val);
  auto ex = m.exists(key);
  check(static_cast<bool>(ex) && caf::get<broker::boolean>(ex->get_data()),
        "store exists reports true after put");
  auto got = m.get(key);
  check(static_cast<bool>(got), "store get succeeds");
  if (got)
    check(caf::get<broker::count>(got->get_data()) == 99u,
          "store get returns put value");
  auto missing = m.get(broker::data{std::string("nope")});
  check(static_cast<bool>(missing) == false, "store get misses unknown key");
  m.erase(key);
  auto ex2 = m.exists(key);
  check(static_cast<bool>(ex2) &&
          caf::get<broker::boolean>(ex2->get_data()) == broker::boolean{false},
        "store exists false after erase");
  ep.shutdown();
  return failures == 0 ? 0 : 1;
}

int test_peer_error() {
  broker::endpoint ep;
  // No retry (retry=0) and nothing listening on the target port: peering
  // must fail fast instead of succeeding.
  bool ok = ep.peer("127.0.0.1", 1, broker::timeout::seconds(0));
  check(!ok, "peer to closed local port fails fast");
  ep.shutdown();
  return failures == 0 ? 0 : 1;
}

int test_status() {
  broker::endpoint ep;
  auto ss = ep.make_status_subscriber(true);
  // Wait a moment and verify the subscriber exists and has no error yet
  // (value_type is variant<broker::none, caf::error, broker::status>).
  auto immediate = ss.get(std::chrono::milliseconds(200));
  check(caf::holds_alternative<broker::none>(immediate),
        "no status/error right after construction");
  ep.shutdown();
  return failures == 0 ? 0 : 1;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) {
    std::cerr << "usage: test_broker <case> [burst-count]\n";
    return 2;
  }
  int rc = 0;
  std::string which = argv[1];
  if (which == "version")
    rc = test_version();
  else if (which == "roundtrip")
    rc = test_roundtrip();
  else if (which == "filter")
    rc = test_filter();
  else if (which == "burst") {
    broker::count n = 1000;
    if (argc > 2)
      n = static_cast<broker::count>(std::stoull(argv[2]));
    rc = test_burst(n);
  }
  else if (which == "store")
    rc = test_store();
  else if (which == "peer_error")
    rc = test_peer_error();
  else if (which == "status")
    rc = test_status();
  else {
    std::cerr << "unknown case: " << which << std::endl;
    return 2;
  }
  std::cout << "case=" << which << " checks=" << checks
            << " failures=" << failures << std::endl;
  if (rc == 0)
    std::cout << "PASS" << std::endl;
  return rc;
}
