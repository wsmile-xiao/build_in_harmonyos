#include <ruckig/ruckig.hpp>

#include <array>
#include <cmath>
#include <cstddef>
#include <iomanip>
#include <iostream>
#include <string>

namespace {

struct TestState {
    int assertions {0};
    int failures {0};

    void check(bool condition, const std::string& label) {
        ++assertions;
        if (condition) {
            std::cout << "[PASS] " << label << '\n';
        } else {
            ++failures;
            std::cerr << "[FAIL] " << label
                      << "; expected=true; actual=false\n";
        }
    }
};

bool near(double actual, double expected, double tolerance = 1e-9) {
    return std::abs(actual - expected) <= tolerance;
}

template<class Actual, class Expected>
bool vector_near(const Actual& actual, const Expected& expected, double tolerance = 1e-8) {
    if (actual.size() != expected.size()) {
        return false;
    }
    for (std::size_t index = 0; index < actual.size(); ++index) {
        if (!near(actual[index], expected[index], tolerance)) {
            return false;
        }
    }
    return true;
}

template<class Vector>
bool vector_finite(const Vector& values) {
    for (const double value : values) {
        if (!std::isfinite(value)) {
            return false;
        }
    }
    return true;
}

template<class Vector>
void print_vector(const std::string& label, const Vector& values) {
    std::cout << "[INFO] " << label << "=[";
    for (std::size_t index = 0; index < values.size(); ++index) {
        if (index != 0) {
            std::cout << ", ";
        }
        std::cout << std::setprecision(17) << values[index];
    }
    std::cout << "]\n";
}

ruckig::InputParameter<3> make_input() {
    ruckig::InputParameter<3> input;
    input.current_position = {0.0, -2.0, 0.0};
    input.current_velocity = {0.0, 0.0, 0.0};
    input.current_acceleration = {0.0, 0.0, 0.0};
    input.target_position = {1.0, -3.0, 2.0};
    input.target_velocity = {0.0, 0.3, 0.0};
    input.target_acceleration = {0.0, 0.0, 0.0};
    input.max_velocity = {1.0, 1.0, 1.0};
    input.max_acceleration = {1.0, 1.0, 1.0};
    input.max_jerk = {1.0, 1.0, 1.0};
    return input;
}

int finish(const TestState& state) {
    if (state.failures == 0) {
        std::cout << "[PASS] summary: " << state.assertions << "/"
                  << state.assertions << " assertions passed\n";
        return 0;
    }
    std::cerr << "[FAIL] summary: " << state.failures << " of "
              << state.assertions << " assertions failed\n";
    return 1;
}

}  // namespace

int main(int argc, char** argv) {
    TestState state;
    if (argc == 2 && std::string(argv[1]) == "--self-test-failure") {
        std::cout << "[STEP] 1/1 verify failure propagation\n";
        state.check(false, "intentional negative-control assertion");
        return finish(state);
    }

    std::cout << "[STEP] 1/4 validate a three-axis input\n";
    const auto input = make_input();
    ruckig::Ruckig<3> offline_ruckig;
    state.check(offline_ruckig.validate_input<false>(input), "valid input accepted");

    std::cout << "[STEP] 2/4 calculate and sample an offline trajectory\n";
    ruckig::Trajectory<3> trajectory;
    const auto calculate_result = offline_ruckig.calculate(input, trajectory);
    const double duration = trajectory.get_duration();
    state.check(calculate_result == ruckig::Result::Working, "offline calculation succeeds");
    state.check(std::isfinite(duration) && duration > 0.0, "duration is finite and positive");

    std::array<double, 3> position {};
    std::array<double, 3> velocity {};
    std::array<double, 3> acceleration {};
    trajectory.at_time(0.0, position, velocity, acceleration);
    state.check(vector_near(position, input.current_position), "start position matches input");
    state.check(vector_near(velocity, input.current_velocity), "start velocity matches input");
    state.check(vector_near(acceleration, input.current_acceleration), "start acceleration matches input");

    trajectory.at_time(duration, position, velocity, acceleration);
    state.check(vector_near(position, input.target_position), "end position matches target");
    state.check(vector_near(velocity, input.target_velocity), "end velocity matches target");
    state.check(vector_near(acceleration, input.target_acceleration), "end acceleration matches target");

    trajectory.at_time(duration / 2.0, position, velocity, acceleration);
    state.check(vector_finite(position), "midpoint position is finite");
    state.check(vector_finite(velocity) && vector_finite(acceleration), "midpoint derivatives are finite");
    state.check(near(duration, 4.0), "known trajectory duration is 4 seconds");

    std::cout << "[STEP] 3/4 execute online updates to the terminal state\n";
    ruckig::Ruckig<3> online_ruckig {0.01};
    auto online_input = make_input();
    ruckig::OutputParameter<3> output;
    ruckig::Result update_result {ruckig::Result::Working};
    const std::size_t max_steps = static_cast<std::size_t>(std::ceil(duration / 0.01)) + 2;
    std::size_t steps = 0;
    do {
        update_result = online_ruckig.update(online_input, output);
        ++steps;
        if (update_result == ruckig::Result::Working) {
            output.pass_to_input(online_input);
        }
    } while (update_result == ruckig::Result::Working && steps <= max_steps);

    auto expected_online_position = input.target_position;
    const double terminal_overrun = output.time - duration;
    for (std::size_t index = 0; index < expected_online_position.size(); ++index) {
        expected_online_position[index] += input.target_velocity[index] * terminal_overrun
            + 0.5 * input.target_acceleration[index] * terminal_overrun * terminal_overrun;
    }
    print_vector("online terminal position", output.new_position);
    print_vector("expected terminal extrapolation", expected_online_position);
    state.check(update_result == ruckig::Result::Finished, "online update reaches Finished");
    state.check(steps > 0 && steps <= max_steps, "online update terminates within the expected bound");
    state.check(vector_near(output.new_position, expected_online_position), "online position matches terminal extrapolation");
    state.check(vector_near(output.new_velocity, input.target_velocity), "online terminal velocity matches target");
    state.check(vector_near(output.new_acceleration, input.target_acceleration), "online terminal acceleration matches target");

    std::cout << "[STEP] 4/4 reject an invalid negative jerk limit\n";
    ruckig::InputParameter<1> invalid;
    invalid.current_position = {0.0};
    invalid.current_velocity = {0.0};
    invalid.current_acceleration = {0.0};
    invalid.target_position = {1.0};
    invalid.target_velocity = {0.0};
    invalid.target_acceleration = {0.0};
    invalid.max_velocity = {1.0};
    invalid.max_acceleration = {1.0};
    invalid.max_jerk = {-1.0};
    ruckig::Ruckig<1> invalid_ruckig;
    state.check(!invalid_ruckig.validate_input<false>(invalid), "negative jerk limit is rejected");

    return finish(state);
}
