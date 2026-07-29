#include <cstdio>
#include "bento4/Ap4.h"

int main(void) {
    // Verify bento4 library is usable by creating a minimal MP4 output stream
    AP4_ByteStream* output = NULL;
    AP4_Result result = AP4_FileByteStream::Create("test.mp4",
                                                    AP4_FileByteStream::STREAM_MODE_WRITE,
                                                    output);
    if (AP4_FAILED(result)) {
        return 1;
    }
    output->Release();
    remove("test.mp4");  // 清理临时文件
    return 0;
}
