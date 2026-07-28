#include <h264bitstream/h264_stream.h>
#include <stdio.h>

int main() {
    h264_stream_t* stream = h264_new();
    if (stream == NULL) {
        fprintf(stderr, "h264_new() returned NULL\n");
        return 1;
    }
    printf("num_seis: %d\n", stream->num_seis);
    h264_free(stream);
    printf("h264bitstream API test passed\n");
    return 0;
}
