#include <cstdio>

extern "C" unsigned long PolyGetPolyVersionNumber(void);

int main()
{
    const unsigned long version = PolyGetPolyVersionNumber();
    if (version == 0)
        return 1;
    std::printf("POLYML_STATIC_CONSUMER_PASS version=%lu\n", version);
    return 0;
}
