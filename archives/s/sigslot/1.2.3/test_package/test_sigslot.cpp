#include <sigslot/signal.hpp>

#include <iostream>
#include <memory>
#include <vector>

namespace {

int failures = 0;
int checks = 0;

void check(bool condition, const char *message) {
    ++checks;
    if (!condition) {
        ++failures;
        std::cerr << "FAIL: " << message << '\n';
    }
}

struct receiver {
    int *value;

    void on_value(int value_to_add) { *value += value_to_add; }
};

}  // namespace

int main() {
    sigslot::signal<int> signal;
    int observed = 0;
    auto connection = signal.connect([&](int value) { observed += value; });

    check(connection.connected(), "connection reports connected");
    check(signal.slot_count() == 1, "signal reports one connected slot");
    signal(3);
    check(observed == 3, "signal emits to a connected lambda");

    connection.block();
    signal(5);
    check(observed == 3, "blocked connection does not receive emissions");
    connection.unblock();
    signal(7);
    check(observed == 10, "unblocked connection receives emissions");

    connection.disconnect();
    signal(11);
    check(observed == 10, "disconnected connection does not receive emissions");
    check(!connection.connected(), "connection reports disconnected");
    check(signal.slot_count() == 0, "signal removes a disconnected slot");

    int scoped_calls = 0;
    {
        sigslot::signal<> scoped_signal;
        sigslot::scoped_connection scoped =
            scoped_signal.connect([&]() { ++scoped_calls; });
        check(scoped_signal.slot_count() == 1, "scoped signal has one slot while alive");
        scoped_signal();
    }
    check(scoped_calls == 1, "scoped connection invokes and disconnects by RAII");

    std::vector<int> order;
    sigslot::signal<> grouped_signal;
    grouped_signal.connect([&]() { order.push_back(2); }, 2);
    grouped_signal.connect([&]() { order.push_back(-1); }, -1);
    grouped_signal.connect([&]() { order.push_back(1); }, 1);
    check(grouped_signal.slot_count() == 3, "grouped signal reports all slots");
    grouped_signal();
    check(order == std::vector<int>({-1, 1, 2}), "slot groups emit in group order");

    sigslot::signal<int> source;
    sigslot::signal<double> sink;
    double chained_value = 0.0;
    sink.connect([&](double value) { chained_value = value; });
    sigslot::connect(source, sink);
    source(4);
    check(chained_value == 4.0, "signals can be chained with compatible arguments");

    int tracked_value = 0;
    sigslot::signal<int> tracked_signal;
    auto tracked_receiver = std::make_shared<receiver>(receiver{&tracked_value});
    auto tracked_connection =
        tracked_signal.connect(&receiver::on_value, tracked_receiver);
    tracked_signal(2);
    tracked_receiver.reset();
    tracked_signal(2);
    check(tracked_value == 2, "tracked slot stops after its shared owner expires");
    check(!tracked_connection.valid(), "expired tracked connection becomes invalid");
    check(tracked_signal.slot_count() == 0, "expired tracked slot is removed");

    if (failures != 0) {
        std::cerr << "sigslot consumer tests failed: " << failures << " of "
                  << checks << " checks failed\n";
        return 1;
    }

    std::cout << "sigslot consumer tests passed: " << checks << " checks\n";
    return 0;
}
