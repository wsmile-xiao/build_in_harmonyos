// HarmonyOS platform-specific test - serialize 1.4.4
//
// This case is complementary to the upstream suite: upstream covers the library
// as a generic bitpacker, while this case pins down behaviour that is decided by
// the HarmonyOS PC (OHOS aarch64, musl) toolchain and ABI rather than by the
// library's own logic. It is built and run by `conan create` under the
// ohos-aarch64 profile and registered as its own CTest case.
//
// Three OHOS-relevant properties are checked:
//   1. Endianness detection - OHOS aarch64 is little endian and clang 15 defines
//      __BYTE_ORDER__, so serialize.h must resolve LITTLE_ENDIAN without needing
//      a user-supplied -DSERIALIZE_LITTLE_ENDIAN. The raw memory probe proves the
//      macro negotiation matched the actual byte order of the target.
//   2. Network byte order identity - the library defines its wire format as
//      little endian, so on OHOS aarch64 host_to_network() must be an identity
//      and the on-the-wire bytes must be LSB-first.
//   3. wchar_t width - OHOS/musl uses a 4 byte wchar_t, which means non-BMP code
//      points (e.g. U+1F600) survive a wstring round trip instead of being
//      rejected by the 2 byte path. The serialized width is still 32 bits per
//      character, so the wire format stays portable.
//
// Checks are explicit (never assert) so they survive Release/NDEBUG builds.
#include <cstdio>
#include <cstring>

#include "serialize.h"

static int failures = 0;

#define CHECK(cond)                                                        \
    do {                                                                   \
        if (!(cond)) {                                                     \
            std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);    \
            ++failures;                                                    \
        }                                                                  \
    } while (0)

int main()
{
    // 1) Endianness detection must agree with the actual target byte order.
    {
        uint32_t value = 0x11223344;
        const unsigned char * bytes = (const unsigned char *) &value;

        CHECK( SERIALIZE_LITTLE_ENDIAN == 1 );
        CHECK( SERIALIZE_BIG_ENDIAN == 0 );
        CHECK( bytes[0] == 0x44 );
        CHECK( bytes[3] == 0x11 );
    }

    // 2) Little endian wire format: host_to_network() is an identity on OHOS.
    {
        const uint32_t value = 0xDEADBEEF;
        CHECK( serialize::host_to_network( value ) == value );
        CHECK( serialize::network_to_host( value ) == value );

        uint8_t buffer[16];
        memset( buffer, 0, sizeof( buffer ) );
        serialize::WriteStream stream( buffer, (int) sizeof( buffer ) );
        CHECK( stream.SerializeBits( 0xDEADBEEF, 32 ) == true );
        stream.Flush();

        CHECK( buffer[0] == 0xEF );
        CHECK( buffer[1] == 0xBE );
        CHECK( buffer[2] == 0xAD );
        CHECK( buffer[3] == 0xDE );

        serialize::ReadStream reader( buffer, 4 );
        uint32_t decoded = 0;
        CHECK( reader.SerializeBits( decoded, 32 ) == true );
        CHECK( decoded == 0xDEADBEEF );
    }

    // 3) OHOS wchar_t is 4 bytes: non-BMP code points survive a round trip.
    {
        CHECK( sizeof( wchar_t ) == 4 );

        wchar_t source[8];
        memset( source, 0, sizeof( source ) );
        source[0] = (wchar_t) 0x1F600;      // emoji, outside the BMP
        source[1] = (wchar_t) 0x043C;       // cyrillic, inside the BMP
        source[2] = (wchar_t) 0xFFFF;       // BMP boundary
        source[3] = L'\0';

        uint8_t buffer[128];
        memset( buffer, 0, sizeof( buffer ) );

        serialize::WriteStream writeStream( buffer, (int) sizeof( buffer ) );
        CHECK( serialize::serialize_wstring_internal( writeStream, source, 8 ) == true );
        writeStream.Flush();

        // 32 bits per character plus the length prefix: independent of wchar_t width.
        const int bytesWritten = writeStream.GetBytesProcessed();
        CHECK( bytesWritten > 0 );
        CHECK( bytesWritten < (int) sizeof( buffer ) );

        wchar_t decoded[8];
        memset( decoded, 0, sizeof( decoded ) );
        serialize::ReadStream readStream( buffer, bytesWritten );
        CHECK( serialize::serialize_wstring_internal( readStream, decoded, 8 ) == true );
        CHECK( decoded[0] == source[0] );
        CHECK( decoded[1] == source[1] );
        CHECK( decoded[2] == source[2] );
        CHECK( decoded[3] == L'\0' );
    }

    if ( failures == 0 )
    {
        std::printf( "test_serialize_ohos: HarmonyOS platform checks passed "
                     "(LE=%d, sizeof(wchar_t)=%zu, %s)\n",
                     SERIALIZE_LITTLE_ENDIAN, sizeof( wchar_t ), SERIALIZE_VERSION );
        return 0;
    }
    std::printf( "test_serialize_ohos: %d check(s) failed\n", failures );
    return 1;
}
