#include <counters/event_counter.h>
#include <counters/bench.h>

int main() {
    counters::event_count first;
    counters::event_count second;
    counters::event_aggregate aggregate;
    aggregate << first;
    aggregate << second;
    if (aggregate.iteration_count() != 2 || aggregate.elapsed_ns() != 0.0 ||
        aggregate.cycles() != 0.0 || aggregate.instructions() != 0.0) {
        return 1;
    }
    const bool available = counters::has_performance_counters();
    (void)available;
    return aggregate.fastest_elapsed_ns() == 0.0 ? 0 : 2;
}
