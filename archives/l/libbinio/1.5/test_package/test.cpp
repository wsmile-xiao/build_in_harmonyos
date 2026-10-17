// test_package/test.cpp — libbinio 1.5 L1 test
// 实质调用 libbinio API: binofstream 写入 int + binifstream 读回校验
#include <libbinio/binfile.h>
#include <cstdio>
#include <cstdlib>

int main(void) {
    const char *tmpfile = "libbinio_test.bin";

    // Write a 32-bit int via binofstream
    binofstream out(tmpfile);
    out.writeInt(0x12345678, 4);
    out.close();

    // Read back via binifstream
    binifstream in(tmpfile);
    long long val = in.readInt(4);
    in.close();

    if (val != 0x12345678) {
        printf("FAIL: readInt = 0x%llX, expected 0x12345678\n", val);
        return 1;
    }

    printf("PASS: libbinio write/read int = 0x%llX\n", val);
    return 0;
}
