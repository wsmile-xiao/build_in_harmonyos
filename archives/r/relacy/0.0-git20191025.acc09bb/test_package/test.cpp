#include <relacy/relacy.hpp>

struct package_smoke : rl::test_suite<package_smoke, 2> {
    rl::var<int> first;
    rl::var<int> second;

    void before() {
        first($) = 0;
        second($) = 0;
    }

    void thread(unsigned index) {
        if (index == 0)
            first($) = 7;
        else
            second($) = 9;
    }

    void after() {
        RL_ASSERT((int)first($) == 7);
        RL_ASSERT((int)second($) == 9);
    }
};

int main() {
    rl::test_params params;
    params.iteration_count = 1000;
    rl::simulate<package_smoke>(params);
    return 0;
}
