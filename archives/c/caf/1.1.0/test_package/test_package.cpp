// CAF consumer smoke test: build a minimal actor system, send a mail,
// and print the version string via caf::get_config / version header.

#include <caf/actor_system.hpp>
#include <caf/actor_system_config.hpp>
#include <caf/event_based_actor.hpp>
#include <caf/init_global_meta_objects.hpp>
#include <caf/scoped_actor.hpp>
#include <caf/typed_actor.hpp>
#include <caf/typed_event_based_actor.hpp>

#include <caf/version.hpp>

#include <chrono>
#include <cstdlib>
#include <iostream>
#include <string>
#include <thread>

namespace {

using ping_actor = caf::typed_actor<caf::result<std::string>(std::string)>;

ping_actor::behavior_type ping_impl() {
  return {
    [](const std::string& who) { return std::string{"pong:"} + who; },
  };
}

} // namespace

int main() {
  // CAF 1.x requires the global meta-object tables before any actor system.
  caf::core::init_global_meta_objects();
  try {
    caf::actor_system_config cfg;
    caf::actor_system sys{cfg};
    auto pinger = sys.spawn(ping_impl);
    std::string res;
    caf::error err;
    caf::scoped_actor self{sys};
    self->mail("hello")
      .request(pinger, std::chrono::seconds(5))
      .receive([&res](const std::string& msg) { res = msg; },
               [&err](caf::error& e) { err = std::move(e); });
    std::cout << "CAF " << CAF_VERSION << " ping result: " << res << '\n';
    if (err) {
      std::cerr << "request failed: " << caf::to_string(err) << '\n';
      return EXIT_FAILURE;
    }
    if (res == "pong:hello")
      return EXIT_SUCCESS;
    std::cerr << "unexpected response: " << res << '\n';
    return EXIT_FAILURE;
  } catch (const std::exception& ex) {
    std::cerr << "exception: " << ex.what() << '\n';
    return EXIT_FAILURE;
  }
}