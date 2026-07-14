#include <stdio.h>
#include <mad.h>

int main(void) {
    /* Verify the library is linkable and the header is usable */
    struct mad_stream stream;
    mad_stream_init(&stream);
    mad_stream_finish(&stream);
    printf("test mad 0.16.4: OK (mad_stream_init/finish succeeded)\n");
    return 0;
}
