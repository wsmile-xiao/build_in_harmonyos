#include <matplot/matplot.h>

int main() {
    const auto values = matplot::linspace(0.0, 1.0, 5);
    return values.size() == 5 && values.front() == 0.0 && values.back() == 1.0 ? 0 : 1;
}
