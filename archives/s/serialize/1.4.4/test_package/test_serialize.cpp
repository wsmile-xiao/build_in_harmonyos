// Consumer test - serialize 1.4.4
//
// Exercises the public API of the installed package from the consumer side
// (R34): the bitpacker primitives, the stream/macro serialization path with a
// write -> read round trip, and the integer/compression helpers. Checks are
// explicit (never assert) so they survive Release/NDEBUG builds.
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

struct Sample
{
    int a;
    float b;
    double c;
    bool flag;
    char text[32];

    template <typename Stream> bool Serialize( Stream & stream )
    {
        serialize_int( stream, a, -1000, 1000 );
        serialize_float( stream, b );
        serialize_double( stream, c );
        serialize_bool( stream, flag );
        serialize_string( stream, text, (int) sizeof( text ) );
        return true;
    }
};

int main()
{
    // 1) Raw bitpacker: mixed width fields round trip through one buffer.
    {
        uint8_t buffer[256];
        memset( buffer, 0, sizeof( buffer ) );

        serialize::BitWriter writer( buffer, sizeof( buffer ) );
        writer.WriteBits( 0, 1 );
        writer.WriteBits( 1, 1 );
        writer.WriteBits( 10, 8 );
        writer.WriteBits( 255, 8 );
        writer.WriteBits( 1000, 10 );
        writer.WriteBits( 50000, 16 );
        writer.WriteBits( 9999999, 32 );
        writer.FlushBits();

        const int expectedBits = 1 + 1 + 8 + 8 + 10 + 16 + 32;
        CHECK( writer.GetBitsWritten() == expectedBits );
        CHECK( writer.GetBytesWritten() == 10 );

        const int bytesWritten = writer.GetBytesWritten();
        serialize::BitReader reader( buffer, bytesWritten );

        CHECK( reader.ReadBits( 1 ) == 0 );
        CHECK( reader.ReadBits( 1 ) == 1 );
        CHECK( reader.ReadBits( 8 ) == 10 );
        CHECK( reader.ReadBits( 8 ) == 255 );
        CHECK( reader.ReadBits( 10 ) == 1000 );
        CHECK( reader.ReadBits( 16 ) == 50000 );
        CHECK( reader.ReadBits( 32 ) == 9999999 );
        CHECK( reader.GetBitsRead() == expectedBits );
    }

    // 2) Stream/macro path: write then read back a struct with mixed types.
    {
        uint8_t buffer[512];
        memset( buffer, 0, sizeof( buffer ) );

        Sample out;
        out.a = -777;
        out.b = 3.5f;
        out.c = 1.0 / 3.0;
        out.flag = true;
        serialize_copy_string( out.text, "harmonyos", sizeof( out.text ) );

        serialize::WriteStream writeStream( buffer, (int) sizeof( buffer ) );
        CHECK( out.Serialize( writeStream ) );
        writeStream.Flush();

        const int bytesWritten = writeStream.GetBytesProcessed();
        CHECK( bytesWritten > 0 );

        Sample in;
        memset( (void*) &in, 0, sizeof( in ) );
        serialize::ReadStream readStream( buffer, bytesWritten );
        CHECK( in.Serialize( readStream ) );

        CHECK( in.a == out.a );
        CHECK( in.b == out.b );
        CHECK( in.c == out.c );
        CHECK( in.flag == out.flag );
        CHECK( strcmp( in.text, out.text ) == 0 );
    }

    // 3) Integer range coding + helper functions.
    {
        uint8_t buffer[64];
        memset( buffer, 0, sizeof( buffer ) );

        serialize::WriteStream stream( buffer, (int) sizeof( buffer ) );
        int value = 42;
        CHECK( stream.SerializeInteger( value, 0, 100 ) == true );
        stream.Flush();

        serialize::ReadStream reader( buffer, stream.GetBytesProcessed() );
        int decoded = 0;
        CHECK( reader.SerializeInteger( decoded, 0, 100 ) == true );
        CHECK( decoded == 42 );

        CHECK( serialize::bits_required( 0, 255 ) == 8 );
        CHECK( serialize::bits_required64( 0, 4294967295ULL ) == 32 );
        CHECK( serialize::unsigned_to_signed( serialize::signed_to_unsigned( -1 ) ) == -1 );
        CHECK( strlen( SERIALIZE_VERSION ) > 0 );
    }

    if ( failures == 0 )
    {
        std::printf( "test_serialize: consumer API verification passed (%s)\n", SERIALIZE_VERSION );
        return 0;
    }
    std::printf( "test_serialize: %d check(s) failed\n", failures );
    return 1;
}
