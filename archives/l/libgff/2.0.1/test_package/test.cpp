#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "gff.h"

// 消费者视角验证：用 libgff 的 GffReader 解析一段真实 GFF3 内容
// （R34：必须实质调用被测包 API）
int main(void) {
    const char* path = "libgff-test.gff3";
    FILE* f = fopen(path, "w");
    if (!f) {
        fprintf(stderr, "cannot create gff input\n");
        return 1;
    }
    fprintf(f, "##gff-version 3\n");
    fprintf(f, "chr1\ttestsrc\tgene\t1000\t9000\t.\t+\t.\tID=gene1;Name=ABC\n");
    fprintf(f, "chr1\ttestsrc\tmRNA\t1000\t9000\t.\t+\t.\tID=tx1;Parent=gene1\n");
    fprintf(f, "chr1\ttestsrc\texon\t1000\t2000\t.\t+\t.\tParent=tx1\n");
    fprintf(f, "chr1\ttestsrc\texon\t3000\t9000\t.\t+\t.\tParent=tx1\n");
    fclose(f);

    GffReader reader(path, true, false);
    reader.readAll(true);

    size_t nfeat = reader.gflst.Count();
    if (nfeat != 1) {
        fprintf(stderr, "FAIL: expected 1 transcript, got %zu\n", nfeat);
        return 1;
    }
    GffObj* feat = reader.gflst[0];
    const char* id = feat ? feat->getID() : nullptr;
    if (!id || strcmp(id, "tx1") != 0) {
        fprintf(stderr, "FAIL: expected id tx1, got %s\n", id ? id : "(null)");
        return 1;
    }
    printf("libgff %s: parse OK (transcript=%s, features=%zu)\n",
           "2.0.1", id, reader.gflst.Count());
    return 0;
}