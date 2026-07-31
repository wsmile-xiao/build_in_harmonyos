#include <Kokkos_Core.hpp>

int main(int argc, char** argv)
{
    Kokkos::initialize(argc, argv);
    int sum = 0;
    Kokkos::parallel_reduce(
        "sum",
        10,
        KOKKOS_LAMBDA(const int i, int& value) { value += i + 1; },
        sum);
    Kokkos::finalize();
    return sum == 55 ? 0 : 1;
}
