// test_package consumer — minimal Boost.SML state machine
#include <boost/sml.hpp>
#include <cassert>
#include <iostream>

namespace sml = boost::sml;

namespace {
struct idle {};
struct running {};
struct start {};
struct stop {};

struct state_machine {
  auto operator()() const {
    using namespace sml;
    return make_transition_table(
        *state<idle> + event<start> / [] { std::cout << "start\n"; } = state<running>,
        state<running> + event<stop> / [] { std::cout << "stop\n"; } = X);
  }
};
}  // namespace

int main() {
  sml::sm<state_machine> sm;
  sm.process_event(start{});
  sm.process_event(stop{});
  assert(sm.is(sml::X));
  std::cout << "boost-sml test_package OK\n";
  return 0;
}