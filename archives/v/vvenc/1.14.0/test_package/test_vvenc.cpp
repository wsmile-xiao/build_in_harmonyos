// Conan test_package — vvenc 1.14.0 consumer use case (HarmonyOS/OHOS).
//
// Checks, from the point of view of a downstream consumer of the packaged
// library:
//   1. the package exports the expected version through the public C API;
//   2. on OHOS the library the process mapped is a plain regular file, not a
//      symlink.  HMDFS cannot follow the symlinks of a versioned shared-library
//      layout, which used to make every consumer abort before main() with
//      "Error loading shared library libvvenc.so.1.14" (Knowledge-Ref E050);
//   3. the public encoder API can be driven end to end: a synthetic YUV420
//      frame is encoded and a non-empty VVC bitstream is retrieved.

#include <cstdio>
#include <cstring>
#include <cstdint>
#include <cstdarg>

#if defined( __OHOS__ )
#include <dlfcn.h>
#include <sys/stat.h>
#include <libgen.h>
#endif

#include "vvenc/vvenc.h"
#include "vvenc/vvencCfg.h"
#include "vvenc/version.h"

static int gChecks   = 0;
static int gFailures = 0;

static void check( bool condition, const char* description )
{
    gChecks++;
    if( !condition )
    {
        gFailures++;
    }
    std::printf( "%-4s %s\n", condition ? "PASS" : "FAIL", description );
}

static void msgFnc( void*, int level, const char* fmt, va_list args )
{
    std::vfprintf( level == 1 ? stderr : stdout, fmt, args );
}

static bool encode_round_trip( int width, int height, int maxFrames )
{
    vvenc_config   cfg;
    vvencEncoder*  enc = nullptr;
    vvencYUVBuffer yuv;
    vvencAccessUnit au;

    int  auCount = 0;
    long long bytes = 0;
    bool encodeDone = false;

    vvenc_init_default( &cfg, width, height, 30, 0, 32, VVENC_FASTER );
    cfg.m_verbosity = VVENC_WARNING;
    vvenc_set_msg_callback( &cfg, nullptr, &msgFnc );
    cfg.m_numThreads = 0;

    enc = vvenc_encoder_create();
    if( enc == nullptr )
    {
        std::printf( "     cannot create encoder\n" );
        return false;
    }

    if( 0 != vvenc_encoder_open( enc, &cfg ) )
    {
        std::printf( "     cannot open encoder: %s\n", vvenc_get_last_error( enc ) );
        vvenc_encoder_close( enc );
        return false;
    }

    vvenc_get_config( enc, &cfg );

    vvenc_YUVBuffer_default( &yuv );
    vvenc_YUVBuffer_alloc_buffer( &yuv, cfg.m_internChromaFormat, cfg.m_SourceWidth, cfg.m_SourceHeight );

    for( int c = 0; c < 3; c++ )
    {
        std::memset( yuv.planes[c].ptr, 512,
                     yuv.planes[c].width * yuv.planes[c].height * sizeof( int16_t ) );
    }

    vvenc_accessUnit_default( &au );
    vvenc_accessUnit_alloc_payload( &au, cfg.m_SourceWidth * cfg.m_SourceHeight );

    bool ok = true;
    for( int frame = 0; frame < maxFrames && ok; frame++ )
    {
        for( int c = 0; c < 3; c++ )
        {
            const unsigned where = ( frame % yuv.planes[c].height ) * yuv.planes[c].stride;
            const uint16_t value = (uint16_t)( ( frame * 37 ) % 256 );
            for( int x = 0; x < yuv.planes[c].width; x++ )
            {
                yuv.planes[c].ptr[where + x] = value;
            }
        }
        yuv.sequenceNumber = frame;

        if( 0 != vvenc_encode( enc, &yuv, &au, &encodeDone ) )
        {
            std::printf( "     encoding failed: %s\n", vvenc_get_last_error( enc ) );
            ok = false;
            break;
        }
        if( au.payloadUsedSize > 0 )
        {
            auCount++;
            bytes += au.payloadUsedSize;
        }
    }

    for( int guard = 0; ok && !encodeDone && guard < 10000; guard++ )
    {
        if( 0 != vvenc_encode( enc, nullptr, &au, &encodeDone ) )
        {
            std::printf( "     flushing failed: %s\n", vvenc_get_last_error( enc ) );
            ok = false;
            break;
        }
        if( au.payloadUsedSize > 0 )
        {
            auCount++;
            bytes += au.payloadUsedSize;
        }
    }

    vvenc_YUVBuffer_free_buffer( &yuv );
    vvenc_accessUnit_free_payload( &au );

    if( 0 != vvenc_encoder_close( enc ) )
    {
        std::printf( "     close encoder failed\n" );
        ok = false;
    }

    std::printf( "     %dx%d, %d frames -> %d access units, %lld bitstream bytes\n",
                 width, height, maxFrames, auCount, bytes );

    return ok && encodeDone && auCount > 0 && bytes > 0;
}

int main()
{
    std::printf( "vvenc test_package (consumer use case)\n" );

    check( vvenc_get_version() != nullptr && std::strcmp( vvenc_get_version(), VVENC_VERSION ) == 0,
           "vvenc_get_version() matches the VVENC_VERSION build macro" );

#if defined( __OHOS__ )
    Dl_info info;
    std::memset( &info, 0, sizeof( info ) );
    if( dladdr( reinterpret_cast<const void*>( &vvenc_encoder_create ), &info ) == 0 ||
        info.dli_fname == nullptr )
    {
        check( false, "libvvenc is resolvable through dladdr()" );
    }
    else
    {
        std::printf( "     mapped from: %s\n", info.dli_fname );

        struct stat lst;
        struct stat st;
        const bool haveLstat = ( lstat( info.dli_fname, &lst ) == 0 );
        const bool haveStat  = ( stat(  info.dli_fname, &st  ) == 0 );

        check( haveStat && S_ISREG( st.st_mode ), "libvvenc maps to a regular file" );
        check( haveLstat && !S_ISLNK( lst.st_mode ),
               "libvvenc is a real file, not a symlink (HMDFS cannot follow symlinks, E050)" );
    }
#else
    check( true, "OHOS specific linkage checks - not applicable" );
#endif

    check( encode_round_trip( 176, 144, 8 ),
           "public encoder API round trip produces a non-empty VVC bitstream" );

    std::printf( "%s: %d of %d check(s) failed\n",
                 gFailures == 0 ? "RESULT PASS" : "RESULT FAIL", gFailures, gChecks );

    return gFailures == 0 ? 0 : 1;
}
