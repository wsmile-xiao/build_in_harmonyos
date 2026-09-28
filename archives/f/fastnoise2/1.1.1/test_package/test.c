#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdbool.h>

/* FastNoise2 public C API */
#include <FastNoise/FastNoise_C.h>

int main(void)
{
    /* Build a noise node tree from its encoded string (public C API).
     * Official upstream string from tools/NodeEditor/util/DemoNodeTrees.inl
     * ("Mountain Terrain" node tree). */
    const char* encoded =
        "E@BBZEG@BD8JFgIECArXIzwECiQIw/UoPwkuAAE@BJDQAH@BC@AIEAJBw@ABZEED0KV78YZmZmPwQDmpkZPwsAAIA/HAMAAHBCBA==";
    void* node = fnNewFromEncodedNodeTree(encoded, ~0u);
    if (node == NULL)
    {
        fprintf(stderr, "fnNewFromEncodedNodeTree returned NULL\n");
        return 1;
    }

    const int size = 4;
    float noise[size * size];
    int pass = 1;

    /* Generate a 4x4 uniform grid via the public C API
     * fnGenUniformGrid2D(node, noiseOut, xOffset, yOffset, xCount, yCount,
     *                    xStepSize, yStepSize, seed, outputMinMax) */
    fnGenUniformGrid2D(node, noise, 0.0f, 0.0f, size, size, 1.0f, 1.0f, 1337, NULL);

    fnDeleteNodeRef(node);

    /* Query active SIMD feature set via public C API (observable platform state) */
    void* probe = fnNewFromEncodedNodeTree(encoded, ~0u);
    if (probe != NULL)
    {
        unsigned fs = fnGetActiveFeatureSet(probe);
        if (fs == 0u)
        {
            fprintf(stderr, "fnGetActiveFeatureSet returned 0\n");
            pass = 0;
        }
        else
        {
            printf("active feature set: %u\n", fs);
        }
        fnDeleteNodeRef(probe);
    }

    /* Verify observable results: every output must be a finite number in the
     * documented [-1, 1] range of a normalized fractal noise generator. */
    for (int i = 0; i < size * size; i++)
    {
        float v = noise[i];
        if (!isfinite((double)v) || v < -1.0f || v > 1.0f)
        {
            fprintf(stderr, "out-of-range noise value: %f at index %d\n", v, i);
            pass = 0;
        }
    }

    if (pass)
    {
        printf("consumer noise[0]=%f noise[15]=%f (finite, in [-1,1]) - PASS\n",
               noise[0], noise[15]);
        return 0;
    }
    return 1;
}