#include <cstdio>
#include <fstream>

#include <bitfield.h>
#include <delta.h>

int main()
{
    DeltaEvent event(23, 7);
    if (event.code() != 23 || event.value() != 7)
        return 1;

    Delta delta;
    delta.inject(41, 9);
    event = delta.event();
    if (event.code() != 41 || event.value() != 9)
        return 2;
    event = delta.event();
    if (event.code() != 0 || event.value() != 0)
        return 3;

    const char *spec_path = "libdjconsole-test.buttons";
    {
        std::ofstream spec(spec_path);
        if (!spec)
            return 4;
        spec << "0 3 17\n";
    }

    Bitfield leds;
    leds.setSize(1);
    if (leds.size() != 1 || !leds.load(spec_path))
        return 5;
    leds.setBit(17);
    if (!leds.dirty() || leds.bits()[0] != 3 || leds.dirty())
        return 6;
    leds.clearBit(17);
    if (leds.bits()[0] != 0)
        return 7;
    std::remove(spec_path);
    return 0;
}
