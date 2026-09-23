#include <boost/sml.hpp>
#include <cassert>
#include <iostream>

// HarmonyOS 消费者验证：真实调用 sml header-only API
// （定义事件/状态/迁移表 → 驱动状态机 → 断言状态迁移结果）

namespace sml = boost::sml;

namespace {
struct unlock_event {};
struct lock_event {};
struct turnstile {
  auto operator()() const {
    using namespace sml;
    // 经典 turnstile 状态机：locked --unlock--> unlocked --lock--> locked
    return make_transition_table(
        *state<class Locked> + event<unlock_event> = state<class Unlocked>,
        state<class Unlocked> + event<lock_event> = state<class Locked>);
  }
};
}  // namespace

int main() {
  using namespace sml;
  sml::sm<turnstile> sm;
  assert(sm.is(sml::state<class Locked>));

  sm.process_event(unlock_event{});
  assert(sm.is(sml::state<class Unlocked>));

  sm.process_event(lock_event{});
  assert(sm.is(sml::state<class Locked>));

  std::cout << "sml 1.1.11 consumer test PASSED (locked->unlocked->locked)"
            << std::endl;
  return 0;
}