/* test_package/test.cpp — dxflib 消费者测试
   验证可链接 libdxflib 并写 ASCII DXF 文件。
*/
#include <dxflib/dl_dxf.h>
#include <cstdio>

int main() {
    const char *dxf_path = "test_consumer.dxf";

    DL_Dxf dxf;
    // DL_DXF::out 仅支持文件名版本（const char* file）
    DL_WriterA *writer = dxf.out(dxf_path, DL_VERSION_2000);
    if (!writer) {
        fprintf(stderr, "FAIL: dxf.out writer failed\n");
        return 1;
    }
    dxf.writeHeader(*writer);
    writer->sectionEnd();
    writer->close();
    delete writer;

    // 验证文件非空
    FILE *f = fopen(dxf_path, "r");
    if (!f) {
        fprintf(stderr, "FAIL: cannot reopen %s\n", dxf_path);
        return 1;
    }
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fclose(f);

    if (size <= 0) {
        fprintf(stderr, "FAIL: DXF file empty (size=%ld)\n", size);
        return 1;
    }

    printf("dxflib smoke test: PASS (DXF write, %ld bytes)\n", size);
    remove(dxf_path);
    return 0;
}
