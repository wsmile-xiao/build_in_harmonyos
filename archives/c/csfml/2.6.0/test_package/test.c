#include <SFML/Network/Packet.h>
#include <SFML/System/Clock.h>
#include <SFML/System/Time.h>

#include <stdint.h>
#include <string.h>

int main(void)
{
    sfClock* clock = sfClock_create();
    sfPacket* packet = sfPacket_create();
    const int32_t expectedNumber = 2600;
    const char* expectedText = "HarmonyOS";
    int32_t actualNumber;
    char actualText[32];
    int result = 0;

    if (!clock || !packet)
        result = 1;
    else
    {
        sfPacket_writeInt32(packet, expectedNumber);
        sfPacket_writeString(packet, expectedText);
        actualNumber = sfPacket_readInt32(packet);
        sfPacket_readString(packet, actualText);

        if (actualNumber != expectedNumber || strcmp(actualText, expectedText) != 0)
            result = 2;
        else if (sfTime_asMicroseconds(sfClock_getElapsedTime(clock)) < 0)
            result = 3;
    }

    // Only destroy objects that were successfully created: CSFML's destroy
    // helpers dereference the inner pointer without a NULL guard, so calling
    // sfPacket_destroy(NULL)/sfClock_destroy(NULL) would segfault when one
    // create succeeded and the other failed (e.g. OOM).
    if (packet)
        sfPacket_destroy(packet);
    if (clock)
        sfClock_destroy(clock);
    return result;
}
