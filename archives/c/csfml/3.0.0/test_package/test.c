/* Consumer test for the csfml/3.0.0 OpenHarmony package: links against the
 * installed libcsfml-system / libcsfml-network only, through the CMake targets
 * exported by the Conan package. */
#include <CSFML/Network/IpAddress.h>
#include <CSFML/Network/Packet.h>
#include <CSFML/System/Clock.h>
#include <CSFML/System/Sleep.h>
#include <CSFML/System/Time.h>

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

static int checks;
static int failures;

#define CHECK(expr)                                                        \
    do {                                                                   \
        ++checks;                                                          \
        if(!(expr))                                                        \
        {                                                                  \
            ++failures;                                                    \
            printf("FAILED %s:%d: %s\n", __FILE__, __LINE__, #expr);       \
        }                                                                  \
    } while(0)

int main(void)
{
    /* System: exported constants are resolved out of libcsfml-system. */
    CHECK(sfTime_Zero.microseconds == 0);
    CHECK(sfTime_asMicroseconds(sfMilliseconds(1500)) == 1500000);
    CHECK(sfTime_asMilliseconds(sfMicroseconds(2500)) == 2);
    CHECK(sfTime_asSeconds(sfSeconds(2.5f)) == 2.5f);

    /* System: clock lifetime. */
    sfClock* clock = sfClock_create();
    CHECK(clock != NULL);
    CHECK(sfClock_isRunning(clock));
    CHECK(sfTime_asMicroseconds(sfClock_getElapsedTime(clock)) >= 0);

    const sfTime before = sfClock_getElapsedTime(clock);
    sfSleep(sfMilliseconds(5));
    CHECK(sfTime_asMicroseconds(sfClock_getElapsedTime(clock)) > sfTime_asMicroseconds(before));

    sfClock* copied = sfClock_copy(clock);
    CHECK(sfTime_asMicroseconds(sfClock_getElapsedTime(copied)) >= sfTime_asMicroseconds(before));
    sfClock_destroy(copied);

    /* System: a stopped clock freezes its elapsed time. */
    sfClock_stop(clock);
    CHECK(!sfClock_isRunning(clock));
    const sfTime stopped = sfClock_getElapsedTime(clock);
    sfSleep(sfMilliseconds(2));
    CHECK(sfTime_asMicroseconds(sfClock_getElapsedTime(clock)) == sfTime_asMicroseconds(stopped));
    sfClock_destroy(clock);

    /* Network: packet round trip. */
    sfPacket* packet = sfPacket_create();
    CHECK(packet != NULL);
    sfPacket_writeInt32(packet, 30000);
    sfPacket_writeInt64(packet, -9000000000LL);
    sfPacket_writeUint8(packet, 214);
    sfPacket_writeBool(packet, true);
    sfPacket_writeFloat(packet, 1.25f);
    sfPacket_writeString(packet, "HarmonyOS");
    CHECK(sfPacket_getDataSize(packet) > 0);

    CHECK(sfPacket_readInt32(packet) == 30000);
    CHECK(sfPacket_readInt64(packet) == -9000000000LL);
    CHECK(sfPacket_readUint8(packet) == 214);
    CHECK(sfPacket_readBool(packet) == true);
    CHECK(sfPacket_readFloat(packet) == 1.25f);

    char text[32] = {0};
    sfPacket_readString(packet, text);
    CHECK(strcmp(text, "HarmonyOS") == 0);
    CHECK(sfPacket_endOfPacket(packet));
    sfPacket_destroy(packet);

    /* Network: address conversion, served by libcsfml-network. */
    CHECK(sfIpAddress_toInteger(sfIpAddress_fromString("192.168.0.1")) == 0xC0A80001u);
    CHECK(sfIpAddress_toInteger(sfIpAddress_fromBytes(8, 8, 8, 8)) == 0x08080808u);
    CHECK(sfIpAddress_toInteger(sfIpAddress_LocalHost) == 0x7F000001u);
    char address[64] = {0};
    sfIpAddress_toString(sfIpAddress_fromInteger(0xC0A80001u), address);
    CHECK(strcmp(address, "192.168.0.1") == 0);

    printf("csfml consumer checks: %d/%d passed\n", checks - failures, checks);
    return failures == 0 ? 0 : 1;
}
