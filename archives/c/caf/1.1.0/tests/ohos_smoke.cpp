// OHOS-specific CAF smoke test.
//
// Exercises real threading and cross-thread message passing on HarmonyOS:
//  1. Verify the runtime builds actors on real worker threads.
//  2. Round-trip messages between N spawned actors (mailbox scheduling).
//  3. Verify atomic counters / synchronization primitives used by CAF on OHOS.
//  4. Report CAF version and platform detection macros.

#include <caf/actor_system.hpp>
#include <caf/actor_system_config.hpp>
#include <caf/blocking_actor.hpp>
#include <caf/event_based_actor.hpp>
#include <caf/init_global_meta_objects.hpp>
#include <caf/scoped_actor.hpp>
#include <caf/typed_actor.hpp>
#include <caf/typed_event_based_actor.hpp>
#include <caf/version.hpp>

#include <atomic>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <string>
#include <thread>

namespace {

constexpr int num_actors = 8;
constexpr int num_roundtrips = 200;

using counter_actor = caf::typed_actor<caf::result<void>(caf::add_atom),
                                       caf::result<int64_t>(caf::get_atom)>;

counter_actor::behavior_type counter_impl(std::shared_ptr<std::atomic<int64_t>> counter) {
  return {
    [counter](caf::add_atom) {
      counter->fetch_add(1, std::memory_order_relaxed);
    },
    [counter](caf::get_atom) { return counter->load(std::memory_order_relaxed); },
  };
}

} // namespace

int main() {
  // CAF 1.x requires the global meta-object tables to be initialized before
  // constructing any actor system instance.
  caf::core::init_global_meta_objects();

  std::cout << "CAF version: " << CAF_VERSION << std::endl;
#if defined(__OHOS__) || defined(OHOS) || defined(__harmonyos__)
  std::cout << "Platform: HarmonyOS detected via macro" << std::endl;
#else
  std::cout << "Platform: OHOS macro not defined by compiler frontend" << std::endl;
#endif
  std::cout << "Hardware concurrency: "
            << std::thread::hardware_concurrency() << std::endl;

  try {
    caf::actor_system_config cfg;
    // Force CAF to actually create multiple scheduler worker threads.
    cfg.set("caf.scheduler.max-threads", 4);
    caf::actor_system sys{cfg};

    auto counter = std::make_shared<std::atomic<int64_t>>(0);
    std::vector<counter_actor> actors;
    for (int i = 0; i < num_actors; ++i)
      actors.emplace_back(sys.spawn(counter_impl, counter));

    {
      caf::scoped_actor self{sys};
      for (int round = 0; round < num_roundtrips; ++round) {
        for (auto& actor : actors) {
          self->mail(caf::add_atom_v).send(actor);
          int64_t result = -1;
          caf::error err;
          self->mail(caf::get_atom_v)
            .request(actor, std::chrono::seconds(5))
            .receive([&result](int64_t value) { result = value; },
                     [&err](caf::error& e) { err = std::move(e); });
          if (err) {
            std::cerr << "get failed: " << caf::to_string(err) << std::endl;
            return EXIT_FAILURE;
          }
          if (result < 0) {
            std::cerr << "OHOS smoke test FAILED: actor request error" << std::endl;
            return EXIT_FAILURE;
          }
        }
      }
    }

    const int64_t expected = static_cast<int64_t>(num_roundtrips * num_actors);
    const int64_t observed = counter->load(std::memory_order_relaxed);
    std::cout << "add_atom processed: " << observed << " (expected " << expected
              << ")" << std::endl;
    if (observed != expected) {
      std::cerr << "OHOS smoke test FAILED: counter mismatch" << std::endl;
      return EXIT_FAILURE;
    }

    // Terminate the counter actors so the system can shut down cleanly.
    {
      caf::scoped_actor self{sys};
      for (auto& actor : actors)
        self->send_exit(actor_cast<caf::actor>(actor),
                        caf::exit_reason::user_shutdown);
    }

    sys.await_all_actors_done();
    std::cout << "OHOS smoke test PASSED" << std::endl;
    return EXIT_SUCCESS;
  } catch (const std::exception& ex) {
    std::cerr << "exception: " << ex.what() << std::endl;
    return EXIT_FAILURE;
  }
}
