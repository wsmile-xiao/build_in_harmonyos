#include <cmath>
#include <ncnn/mat.h>

int main() {
    ncnn::Mat values(4);
    values.fill(2.5f);
    if (values.total() != 4) return 1;
    const float *data = values;
    for (int i = 0; i < 4; ++i) {
        if (std::fabs(data[i] - 2.5f) > 0.0001f) return 2;
    }
    return 0;
}
