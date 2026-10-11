#include <PtexHalf.h>

#include <cstdio>

int main()
{
    Ptex::PtexHalf half(1.5f);
    if (static_cast<float>(half) != 1.5f)
        return 1;
    std::puts("PTEX_CONSUMER_1_OF_1_PASS");
    return 0;
}
