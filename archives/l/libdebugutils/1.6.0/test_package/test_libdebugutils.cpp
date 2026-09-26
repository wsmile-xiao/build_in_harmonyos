#include <cmath>
#include <cstdio>

#include "DebugDraw.h"

class CaptureDraw : public duDebugDraw
{
public:
    CaptureDraw() : primitive(DU_DRAW_POINTS), begins(0), ends(0), vertices(0), invalid(false) {}

    void depthMask(bool) override {}
    void texture(bool) override {}

    void begin(duDebugDrawPrimitives prim, float) override
    {
        primitive = prim;
        ++begins;
    }

    void vertex(const float* pos, unsigned int) override
    {
        vertex(pos[0], pos[1], pos[2], 0);
    }

    void vertex(float x, float y, float z, unsigned int) override
    {
        invalid = invalid || !std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z);
        ++vertices;
    }

    void vertex(const float* pos, unsigned int color, const float*) override
    {
        vertex(pos, color);
    }

    void vertex(float x, float y, float z, unsigned int color, float, float) override
    {
        vertex(x, y, z, color);
    }

    void end() override { ++ends; }

    duDebugDrawPrimitives primitive;
    int begins;
    int ends;
    int vertices;
    bool invalid;
};

int main()
{
    const unsigned int color = duRGBA(64, 128, 192, 255);
    CaptureDraw capture;
    duDebugDrawCircle(&capture, 3.0f, 4.0f, 5.0f, 2.0f, color, 2.0f);

    if (capture.begins != 1 || capture.ends != 1 ||
        capture.primitive != DU_DRAW_LINES || capture.vertices < 32 || capture.invalid)
    {
        std::fprintf(stderr, "DebugUtils circle draw failed: begin=%d end=%d vertices=%d invalid=%d\n",
                     capture.begins, capture.ends, capture.vertices, capture.invalid ? 1 : 0);
        return 1;
    }

    std::printf("CHECK-OK: DebugUtils circle generated %d finite line vertices\n", capture.vertices);
    return 0;
}
