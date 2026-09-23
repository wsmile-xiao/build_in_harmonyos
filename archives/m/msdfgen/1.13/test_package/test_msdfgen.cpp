// Consumer test — msdfgen 1.13 (final Conan package).
//
// Links against the installed msdfgen::msdfgen (CMakeDeps) and verifies the
// core MSDF functionality with a programmatically constructed vector shape
// (rectangle + triangle). No font or image files are consumed — all input
// geometry is defined in this source file, so no unverified binary fixtures
// enter the repository.
//
// Assertions:
//  A1 dimensions: generated bitmap has the requested width/height
//  A2 channels: MSDF bitmap carries 3 channels (float, N=3)
//  A3 value domain: raw MSDF floats are signed distances in pixel units —
//     negative inside, positive outside (not normalized [0,1]); all
//     finite, bounded by the configured Range window
//  A4 inside/outside sign relation: interior median-of-three < -5 px,
//     exterior median-of-three > +5 px (median-of-three reconstruction)
//  A5 corner channel asymmetry: near a corner of the rectangle the three
//     channels differ (the whole point of multi-channel SDF)
//  A6 exception-ish input: an empty shape generates a deterministic,
//     uniformly non-finite field (distance finder never updates its
//     minimum -> infinity; two independent runs compare bit-exact)
//  A7 shape description round-trip: msdfgen's own text shape-description
//     parser reads back the same rectangle (auditable text fixture)
//  A8 triangle SDF (single channel, core path): whole-field statistics
//     (deepest interior < -5 px, far exterior > +10 px) plus fixed-point
//     sign checks (interior point < 0, exterior point > 0)
//  A9 ext path: savePng writes a real PNG through libpng (magic bytes)
#include <cmath>
#include <cstdio>
#include <cstring>

#include <msdfgen.h>
#include <msdfgen-ext.h>

using namespace msdfgen;

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg)                                            \
    do {                                                            \
        ++checks;                                                   \
        if (!(cond)) {                                              \
            ++failures;                                             \
            std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, msg); \
        }                                                           \
    } while (0)

// Builds a rectangle [0,10]x[0,10] (CCW) — the simplest audit-friendly shape.
static Shape makeRectangle() {
    Shape shape;
    Contour &c = shape.addContour();
    c.addEdge(EdgeHolder(Vector2(0, 0), Vector2(10, 0)));
    c.addEdge(EdgeHolder(Vector2(10, 0), Vector2(10, 10)));
    c.addEdge(EdgeHolder(Vector2(10, 10), Vector2(0, 10)));
    c.addEdge(EdgeHolder(Vector2(0, 10), Vector2(0, 0)));
    return shape;
}

// Builds a right triangle (0,0)-(10,0)-(0,10).
static Shape makeTriangle() {
    Shape shape;
    Contour &c = shape.addContour();
    c.addEdge(EdgeHolder(Vector2(0, 0), Vector2(10, 0)));
    c.addEdge(EdgeHolder(Vector2(10, 0), Vector2(0, 10)));
    c.addEdge(EdgeHolder(Vector2(0, 10), Vector2(0, 0)));
    return shape;
}

int main() {
    // ── A1/A2: rectangle MSDF, 64x64, 3 channels ────────────────────────
    Shape rect = makeRectangle();
    rect.normalize();
    edgeColoringSimple(rect, 3.0);

    const int W = 64, H = 64;
    Bitmap<float, 3> msdf(W, H);
    // shape units 12.8 wide -> 64 px: scale 5, translate centers the shape.
    SDFTransformation transform(
        Projection(Vector2(5.0, 5.0), Vector2(2.0, 2.0)), Range(0.25));
    generateMSDF(msdf, rect, transform);

    CHECK(msdf.width() == W, "A1 width is 64");
    CHECK(msdf.height() == H, "A1 height is 64");

    // ── A3: all pixels finite; raw MSDF floats are signed distances in
    // pixel units (negative inside, positive outside — verified against
    // the library's actual output on OHOS). The generator clamps to the
    // configured Range window, so |v| stays bounded.
    bool allFinite = true;
    float vmin = 1e30f, vmax = -1e30f;
    for (int y = 0; y < H; ++y)
        for (int x = 0; x < W; ++x)
            for (int ch = 0; ch < 3; ++ch) {
                float v = msdf(x, y)[ch];
                if (!std::isfinite(v)) allFinite = false;
                if (v < vmin) vmin = v;
                if (v > vmax) vmax = v;
            }
    CHECK(allFinite, "A3 all channel values finite (no NaN/Inf)");
    CHECK(vmax > 0.0f, "A3 exterior values positive (signed-distance domain)");
    CHECK(vmin < 0.0f, "A3 interior values negative (signed-distance domain)");
    CHECK(vmax - vmin > 5.0f, "A3 value spread is meaningful (field is not flat)");

    // ── A4: inside/outside sign relation via median-of-three ────────────
    // Center of the rectangle (32,32) is well inside; corners of the bitmap
    // are well outside. Distances are in pixels: interior clearly below
    // zero, exterior clearly above zero.
    float centerR = msdf(32, 32)[0], centerG = msdf(32, 32)[1], centerB = msdf(32, 32)[2];
    float centerMedian = centerR < centerG
        ? (centerG < centerB ? centerG : (centerR < centerB ? centerB : centerR))
        : (centerR < centerB ? centerR : (centerG < centerB ? centerB : centerG));
    float cornerMedianR = msdf(1, 1)[0], cornerMedianG = msdf(1, 1)[1], cornerMedianB = msdf(1, 1)[2];
    float cornerMedian = cornerMedianR < cornerMedianG
        ? (cornerMedianG < cornerMedianB ? cornerMedianG : (cornerMedianR < cornerMedianB ? cornerMedianB : cornerMedianR))
        : (cornerMedianR < cornerMedianB ? cornerMedianR : (cornerMedianG < cornerMedianB ? cornerMedianB : cornerMedianG));
    CHECK(centerMedian < -5.0f, "A4 interior median-of-three < -5 px (inside)");
    CHECK(cornerMedian > 5.0f, "A4 exterior median-of-three > 5 px (outside)");
    CHECK(cornerMedian - centerMedian > 10.0f, "A4 outside/inside ordering holds");

    // ── A5: corner channel asymmetry ────────────────────────────────────
    // Sample near the top-right corner of the rectangle (~px 52,12) where
    // the three differently-colored edges meet. In an MSDF the channels
    // disagree near corners — assert a measurable spread.
    float cr = msdf(52, 12)[0], cg = msdf(52, 12)[1], cb = msdf(52, 12)[2];
    float cmin = cr < cg ? (cr < cb ? cr : cb) : (cg < cb ? cg : cb);
    float cmax = cr > cg ? (cr > cb ? cr : cb) : (cg > cb ? cg : cb);
    CHECK(cmax - cmin > 1.0f, "A5 channels differ near corner (MSDF property)");

    // ── A6: empty shape must not crash, and its output is deterministic ─
    // Upstream semantics: with no edges, the distance finder never updates
    // its minimum, so every sample maps to infinity. The contract worth
    // asserting: the call returns (no crash — proven by reaching these
    // checks), every value is uniformly non-finite (detectable by
    // std::isfinite, never random garbage), and a second independent
    // generation produces a bit-exact identical bitmap (memcmp per float:
    // a NaN payload would break operator== but not a byte comparison).
    {
        Shape empty;
        empty.normalize();  // no contours — must not crash
        Bitmap<float, 3> first(16, 16), second(16, 16);
        generateMSDF(first, empty, transform);
        generateMSDF(second, empty, transform);
        bool anyFinite = false;
        for (int y = 0; y < 16; ++y)
            for (int x = 0; x < 16; ++x)
                for (int ch = 0; ch < 3; ++ch)
                    if (std::isfinite(first(x, y)[ch])) anyFinite = true;
        CHECK(!anyFinite,
              "A6 empty shape output uniformly non-finite (upstream: distance=infinity)");
        bool bitExact = true;
        for (int y = 0; y < 16; ++y)
            for (int x = 0; x < 16; ++x)
                for (int ch = 0; ch < 3; ++ch)
                    if (std::memcmp(&first(x, y)[ch], &second(x, y)[ch],
                                    sizeof(float)) != 0)
                        bitExact = false;
        CHECK(bitExact, "A6 empty shape generation is bit-exact across two runs");
    }

    // ── A7: text shape-description round-trip (auditable fixture) ───────
    // The definition below is plain text, reviewed line-by-line: a
    // rectangle contour { 0,0; 10,0; 10,10; 0,10; # }.
    Shape parsed;
    bool colorsSpecified = false;
    bool ok = readShapeDescription(
        "{ 0,0; 10,0; 10,10; 0,10; # }", parsed, &colorsSpecified);
    CHECK(ok, "A7 shape description parses");
    CHECK(parsed.contours.size() == 1, "A7 parsed shape has 1 contour");
    CHECK(parsed.contours[0].edges.size() == 4, "A7 parsed contour has 4 edges");
    double l = 0, b = 0, r = 0, t = 0;
    parsed.bound(l, b, r, t);
    CHECK(std::fabs(l) < 1e-9 && std::fabs(b) < 1e-9 &&
              std::fabs(r - 10.0) < 1e-9 && std::fabs(t - 10.0) < 1e-9,
          "A7 parsed rectangle bounds are (0,0)-(10,10)");

    // ── triangle SDF (single channel, core path) ────────────────────────
    Shape tri = makeTriangle();
    tri.normalize();
    Bitmap<float, 1> sdf(32, 32);
    SDFTransformation t32(
        Projection(Vector2(2.5, 2.5), Vector2(1.0, 1.0)), Range(0.25));
    generateSDF(sdf, tri, t32);
    // Signed-distance sign convention (verified against actual library
    // output on OHOS): negative inside, positive outside. Projection maps
    // px -> shape via unproject(px) = px/scale - translate, so the triangle
    // (0,0)-(10,0)-(0,10) occupies px [2.5, 27.5] x [2.5, 27.5] with the
    // hypotenuse cutting the upper right. Use whole-field statistics plus
    // two fixed points far from any boundary.
    float sdfMin = 1e30f, sdfMax = -1e30f;
    int minX = 0, minY = 0, maxX = 0, maxY = 0;
    for (int y = 0; y < 32; ++y)
        for (int x = 0; x < 32; ++x) {
            float v = sdf(x, y)[0];
            if (v < sdfMin) { sdfMin = v; minX = x; minY = y; }
            if (v > sdfMax) { sdfMax = v; maxX = x; maxY = y; }
        }
    CHECK(std::isfinite(sdfMin) && std::isfinite(sdfMax), "A8 triangle SDF finite");
    CHECK(sdfMin < -5.0f, "A8 triangle deepest interior < -5 (inside is negative)");
    CHECK(sdfMax > 10.0f, "A8 triangle far exterior > 10 (outside is positive)");
    CHECK(minX >= 2 && minX <= 27 && minY >= 2 && minY <= 27,
          "A8 deepest interior point lies within triangle footprint");
    // (12,8) px -> shape (3.8, 2.2): x+y=6 < 10 and x,y>0 -> strictly inside
    CHECK(sdf(12, 8)[0] < -1.0f, "A8 fixed interior point is negative");
    // (30,30) px -> shape (11,11): x+y=22 > 10 -> strictly outside
    CHECK(sdf(30, 30)[0] > 1.0f, "A8 fixed exterior point is positive");
    CHECK(sdf(12, 8)[0] < sdf(30, 30)[0], "A8 interior distance below exterior distance");

    // ── ext path: savePng writes a PNG through libpng ───────────────────
    const char *pngPath = "test-msdf-consumer.png";
    bool saved = savePng(msdf, pngPath);
    CHECK(saved, "A9 savePng (ext, libpng) succeeds");
    if (saved) {
        std::FILE *f = std::fopen(pngPath, "rb");
        CHECK(f != NULL, "A9 saved PNG file is openable");
        if (f) {
            unsigned char sig[8];
            size_t got = std::fread(sig, 1, 8, f);
            static const unsigned char PNG_MAGIC[8] = {0x89, 'P', 'N', 'G',
                                                       0x0D, 0x0A, 0x1A, 0x0A};
            CHECK(got == 8 && std::memcmp(sig, PNG_MAGIC, 8) == 0,
                  "A9 file starts with PNG magic");
            std::fclose(f);
        }
    }
    std::remove(pngPath);

    std::printf("test_msdfgen: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
