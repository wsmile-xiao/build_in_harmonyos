#include <hdr/hdr_histogram.h>

#include <stdint.h>
#include <stdio.h>

int main(void)
{
    struct hdr_histogram* histogram = NULL;
    int rc = hdr_init(1, INT64_C(3600000000), 3, &histogram);
    if (rc != 0 || histogram == NULL)
    {
        fprintf(stderr, "hdr_init failed: %d\n", rc);
        return 1;
    }

    if (!hdr_record_value(histogram, 42) || !hdr_record_values(histogram, 1000, 3))
    {
        fprintf(stderr, "failed to record values\n");
        hdr_close(histogram);
        return 1;
    }

    if (histogram->total_count != 4 || hdr_max(histogram) != 1000)
    {
        fprintf(stderr, "unexpected histogram statistics\n");
        hdr_close(histogram);
        return 1;
    }

    printf("hdrhistogram smoke test passed: total=%ld max=%ld\n",
           (long)histogram->total_count, (long)hdr_max(histogram));
    hdr_close(histogram);
    return 0;
}
