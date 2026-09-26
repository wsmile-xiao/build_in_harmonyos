/* ====================================================================================
 * test_package/test_orb.c — consumer-side API test for the packaged liborb.
 *
 * Links against the installed liborb shared library and drives the public COBS
 * framing API from <cobs.h> (the same API the upstream Tests/test_cobs.c suite
 * covers) to prove that the adapted library is usable by a downstream project.
 * ==================================================================================== */

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "cobs.h"

static int g_checks;
static int g_failures;

static void _check( bool ok, const char *what )
{
    g_checks++;
    if ( !ok )
    {
        g_failures++;
        fprintf( stderr, "FAIL: %s\n", what );
    }
    else
    {
        fprintf( stderr, "PASS: %s\n", what );
    }
}

/* --- streaming decoder callback ---------------------------------------------------- */

static struct Frame g_pumped;
static int          g_pumpedCount;

static void _onFrame( struct Frame *frame, void *param )
{
    ( void )param;
    g_pumped = *frame;
    g_pumpedCount++;
}

int main( void )
{
    /* A payload deliberately full of 0x00 bytes to exercise COBS framing. */
    static const uint8_t payload[] =
        { 0x00, 0x11, 0x00, 0x22, 0x33, 0x00, 0x00, 0x44 };
    static const uint8_t plain[] =
        { 0x41, 0x42, 0x43, 0x44, 0x45 };

    struct Frame enc;
    struct Frame dec;

    /* 1. encode a payload containing 0x00 bytes */
    COBSEncode( NULL, 0, NULL, 0, payload, ( int )sizeof( payload ), &enc );
    _check( enc.len > sizeof( payload ), "COBSEncode() adds COBS framing overhead" );

    /* 2. the frame extent helper agrees with the encoded length */
    {
        const uint8_t *extent = COBSgetFrameExtent( enc.d, ( int )enc.len );
        _check( extent != NULL && ( size_t )( extent - enc.d ) + 1 == enc.len,
                "COBSgetFrameExtent() spans the whole encoded frame" );
    }

    /* 3. context-free decode round trip */
    memset( &dec, 0, sizeof( dec ) );
    _check( COBSSimpleDecode( enc.d, ( int )enc.len, &dec ),
            "COBSSimpleDecode() accepts the encoded frame" );
    _check( dec.len == sizeof( payload ) &&
            memcmp( dec.d, payload, sizeof( payload ) ) == 0,
            "COBSSimpleDecode() reproduces the original payload" );

    /* 4. encode/decode round trip for a 0x00-free payload */
    {
        struct Frame enc2;
        struct Frame dec2;
        COBSEncode( NULL, 0, NULL, 0, plain, ( int )sizeof( plain ), &enc2 );
        memset( &dec2, 0, sizeof( dec2 ) );
        COBSSimpleDecode( enc2.d, ( int )enc2.len, &dec2 );
        _check( dec2.len == sizeof( plain ) &&
                memcmp( dec2.d, plain, sizeof( plain ) ) == 0,
                "COBS round trip preserves a 0x00-free payload" );
    }

    /* 5. streaming decoder (COBSInit / COBSPump / COBSDelete) */
    {
        struct COBS *decoder = COBSInit( NULL );
        _check( decoder != NULL, "COBSInit() returns a decoder context" );
        if ( decoder != NULL )
        {
            g_pumpedCount = 0;
            memset( &g_pumped, 0, sizeof( g_pumped ) );
            COBSPump( decoder, enc.d, ( int )enc.len, _onFrame, NULL );
            _check( g_pumpedCount == 1 &&
                    g_pumped.len == sizeof( payload ) &&
                    memcmp( g_pumped.d, payload, sizeof( payload ) ) == 0,
                    "COBSPump() streams the same payload" );
            _check( COBSGetErrors( decoder ) == 0,
                    "COBSPump() reported no framing errors" );
            COBSDelete( decoder );
        }
    }

    fprintf( stderr, "\nliborb COBS API: %d/%d checks passed\n",
             g_checks - g_failures, g_checks );
    return g_failures == 0 ? 0 : 1;
}
