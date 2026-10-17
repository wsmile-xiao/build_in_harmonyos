#include <mp/fsm.h>
#include <variant>

struct event_connect {};
struct event_disconnect {};
struct state_idle {};
struct state_connected {};
using state = std::variant<state_idle, state_connected>;

class sample_fsm : public mp::fsm<sample_fsm, state> {
public:
    template<typename S, typename E>
    auto on_event(S&, const E&) { return std::nullopt; }
    auto on_event(state_idle&, const event_connect&) { return state_connected{}; }
    auto on_event(state_connected&, const event_disconnect&) { return state_idle{}; }
};

int main() {
    sample_fsm fsm;
    if (!std::holds_alternative<state_idle>(fsm.get_state())) return 1;
    fsm.dispatch(event_connect{});
    if (!std::holds_alternative<state_connected>(fsm.get_state())) return 2;
    fsm.dispatch(event_disconnect{});
    return std::holds_alternative<state_idle>(fsm.get_state()) ? 0 : 3;
}
