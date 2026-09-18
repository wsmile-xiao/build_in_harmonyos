/* jxrlib test_package consumer: in-memory encode -> file -> decode roundtrip.
 *
 * Real consumer of the packaged jxrlib libraries (R34): drives the public
 * PK* glue API exactly like upstream JxrEncApp/JxrDecApp do — codec factory,
 * WMPEncoder over a WMPStream, WMPEncoder decode-back via
 * CreateDecoderFromFile + PKFormatConverter::Copy — and asserts dimensions,
 * pixel format and near-lossless pixel identity (quality 1).
 */
#include <stdio.h>
#include <string.h>

#include <JXRTest.h>

#define WIDTH 32
#define HEIGHT 32
#define STRIDE (WIDTH * 3)
#define TOLERANCE 3

static int g_checks;
static int g_failures;

#define CHECK(cond) \
    do { \
        ++g_checks; \
        if (!(cond)) { \
            ++g_failures; \
            fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #cond); \
        } \
    } while (0)

int main(void)
{
    static const char *kFile = "consumer_roundtrip.jxr";
    PKFactory *pFactory = NULL;
    PKCodecFactory *pCodecFactory = NULL;
    PKImageEncode *pEncoder = NULL;
    PKImageDecode *pDecoder = NULL;
    PKFormatConverter *pConverter = NULL;
    struct WMPStream *pStream = NULL;
    CWMIStrCodecParam wmiSCP;
    PKPixelFormatGUID fmt;
    PKRect rect;
    U8 src[HEIGHT * STRIDE];
    U8 dst[HEIGHT * STRIDE];
    I32 w = 0;
    I32 h = 0;
    ERR err;
    int x;
    int y;
    long maxdiff = 0;
    long total = 0;

    /* Encode params mirror upstream JxrEncApp defaults (quality 1). */
    memset(&wmiSCP, 0, sizeof(wmiSCP));
    wmiSCP.bVerbose = FALSE;
    wmiSCP.cfColorFormat = YUV_444;
    wmiSCP.bdBitDepth = BD_LONG;
    wmiSCP.bfBitstreamFormat = FREQUENCY;
    wmiSCP.bProgressiveMode = TRUE;
    wmiSCP.olOverlap = OL_ONE;
    wmiSCP.cNumOfSliceMinus1H = 0;
    wmiSCP.cNumOfSliceMinus1V = 0;
    wmiSCP.sbSubband = SB_ALL;
    wmiSCP.uAlphaMode = 0;
    wmiSCP.uiDefaultQPIndex = 1;
    wmiSCP.uiDefaultQPIndexAlpha = 1;

    /* 32x24bpp RGB gradient source. */
    for (y = 0; y < HEIGHT; ++y) {
        for (x = 0; x < WIDTH; ++x) {
            src[y * STRIDE + x * 3 + 0] = (U8)(x * 8);
            src[y * STRIDE + x * 3 + 1] = (U8)(y * 8);
            src[y * STRIDE + x * 3 + 2] = (U8)((x + y) * 4);
        }
    }

    err = PKCreateFactory(&pFactory, PK_SDK_VERSION);
    CHECK(WMP_errSuccess == err && NULL != pFactory);
    err = PKCreateCodecFactory(&pCodecFactory, WMP_SDK_VERSION);
    CHECK(WMP_errSuccess == err && NULL != pCodecFactory);

    /* Encode: stream + WMPEncoder -> jxr file. */
    remove(kFile);
    err = pFactory->CreateStreamFromFilename(&pStream, kFile, "wb");
    CHECK(WMP_errSuccess == err && NULL != pStream);
    err = pCodecFactory->CreateCodec(&IID_PKImageWmpEncode, (void **)&pEncoder);
    CHECK(WMP_errSuccess == err && NULL != pEncoder);

    err = pEncoder->Initialize(pEncoder, pStream, &wmiSCP, sizeof(wmiSCP));
    CHECK(WMP_errSuccess == err);
    err = pEncoder->SetPixelFormat(pEncoder, GUID_PKPixelFormat24bppRGB);
    CHECK(WMP_errSuccess == err);
    err = pEncoder->SetSize(pEncoder, WIDTH, HEIGHT);
    CHECK(WMP_errSuccess == err);
    err = pEncoder->SetResolution(pEncoder, 96.0F, 96.0F);
    CHECK(WMP_errSuccess == err);
    err = pEncoder->WritePixels(pEncoder, HEIGHT, src, STRIDE);
    CHECK(WMP_errSuccess == err);
    err = pEncoder->Release(&pEncoder); /* closes the stream */
    pEncoder = NULL;
    CHECK(WMP_errSuccess == err);

    /* The container must exist on disk with real content. */
    {
        FILE *f = fopen(kFile, "rb");
        long sz = -1;
        CHECK(NULL != f);
        if (NULL != f) {
            CHECK(0 == fseek(f, 0, SEEK_END));
            sz = ftell(f);
            fclose(f);
        }
        CHECK(sz > 64);
    }

    /* Decode back through the codec factory. */
    err = pCodecFactory->CreateDecoderFromFile(kFile, &pDecoder);
    CHECK(WMP_errSuccess == err && NULL != pDecoder);
    err = pDecoder->GetSize(pDecoder, &w, &h);
    CHECK(WMP_errSuccess == err);
    CHECK(WIDTH == w && HEIGHT == h);
    err = pDecoder->GetPixelFormat(pDecoder, &fmt);
    CHECK(WMP_errSuccess == err);
    CHECK(IsEqualGUID(&fmt, &GUID_PKPixelFormat24bppRGB));

    err = pCodecFactory->CreateFormatConverter(&pConverter);
    CHECK(WMP_errSuccess == err && NULL != pConverter);
    err = pConverter->Initialize(pConverter, pDecoder, "jxr", GUID_PKPixelFormat24bppRGB);
    CHECK(WMP_errSuccess == err);
    memset(dst, 0, sizeof(dst));
    rect.X = 0;
    rect.Y = 0;
    rect.Width = WIDTH;
    rect.Height = HEIGHT;
    err = pConverter->Copy(pConverter, &rect, dst, STRIDE);
    CHECK(WMP_errSuccess == err);
    pConverter->Release(&pConverter);
    pConverter = NULL;

    /* Near-lossless identity: every byte within TOLERANCE, non-degenerate. */
    for (y = 0; y < HEIGHT * STRIDE; ++y) {
        long d = dst[y] > src[y] ? (long)(dst[y] - src[y]) : (long)(src[y] - dst[y]);
        if (d > maxdiff) {
            maxdiff = d;
        }
        total += d;
    }
    CHECK(maxdiff <= TOLERANCE);
    CHECK(total * 2 < (long)(HEIGHT * STRIDE) * TOLERANCE);

    pDecoder->Release(&pDecoder);
    pCodecFactory->Release(&pCodecFactory);
    pFactory->Release(&pFactory);
    remove(kFile);

    printf("checks=%d failures=%d maxdiff=%ld\n", g_checks, g_failures, maxdiff);
    if (0 == g_failures && g_checks >= 20) {
        printf("jxrlib consumer roundtrip: PASS\n");
        return 0;
    }
    fprintf(stderr, "jxrlib consumer roundtrip: FAIL\n");
    return 1;
}
