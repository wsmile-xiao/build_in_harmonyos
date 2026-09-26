#include <cvd/image.h>
#include <cvd/timer.h>

int main()
{
    CVD::Image<int> image(CVD::ImageRef(2, 2));
    image[0][0] = 42;
    image[1][1] = 7;

    if (image.size() != CVD::ImageRef(2, 2) || image[0][0] != 42 ||
        image[1][1] != 7)
        return 1;

    // Non-inline symbol: verifies the consumer really links libcvd.
    if (CVD::get_time_of_day() <= 0)
        return 2;
    return 0;
}
