// Consumer test for libgff 2.0.0.
// Parses an inline GFF3 annotation with the public GffReader API and asserts
// the resulting transcript/gene IDs, exon count and attributes.

#include <cstdio>
#include <cstring>
#include <fstream>

#include "gff.h"

static int g_checks = 0;
static int g_failures = 0;

static void check(bool ok, const char* expr, int line) {
    ++g_checks;
    if (!ok) {
        std::fprintf(stderr, "FAIL(line %d): %s\n", line, expr);
        ++g_failures;
    }
}

#define CHECK(expr) check((expr), #expr, __LINE__)

int main() {
    const char* gff_path = "consumer_input.gff3";
    {
        std::ofstream out(gff_path);
        if (!out) {
            std::fprintf(stderr, "cannot create %s\n", gff_path);
            return 2;
        }
        out << "##gff-version 3\n"
            << "chr1\tlibgff-test\tgene\t1000\t2200\t.\t+\t.\tID=gene1;Name=GENE1\n"
            << "chr1\tlibgff-test\tmRNA\t1000\t2200\t.\t+\t.\tID=tx1;Parent=gene1;biotype=protein_coding\n"
            << "chr1\tlibgff-test\texon\t1000\t1200\t.\t+\t.\tID=exon1;Parent=tx1\n"
            << "chr1\tlibgff-test\texon\t1500\t2200\t.\t+\t.\tID=exon2;Parent=tx1\n";
    }

    GffReader reader(gff_path, true, false);
    reader.readAll(true);

    const int nrecords = reader.gflst.Count();
    CHECK(nrecords >= 1);

    GffObj* tx = NULL;
    for (int i = 0; i < nrecords; ++i) {
        GffObj* f = reader.gflst[i];
        if (f != NULL && f->isTranscript()) {
            tx = f;
            break;
        }
    }
    CHECK(tx != NULL);

    if (tx != NULL) {
        CHECK(tx->getID() != NULL && std::strcmp(tx->getID(), "tx1") == 0);
        CHECK(tx->getGeneID() != NULL && std::strcmp(tx->getGeneID(), "gene1") == 0);
        CHECK(tx->exons.Count() == 2);

        // ID/Parent 是解析器消费的结构属性（分别进入 gffID/geneID），不保留在 attrs 表，
        // 用自定义属性验证 getAttr 路径。
        const char* attr_biotype = tx->getAttr("biotype");
        CHECK(attr_biotype != NULL && std::strcmp(attr_biotype, "protein_coding") == 0);

        CHECK(tx->attrs != NULL && tx->attrs->Count() > 0);
    }

    std::remove(gff_path);

    if (g_failures == 0) {
        std::printf("libgff consumer test: %d/%d checks passed\n", g_checks, g_checks);
        return 0;
    }
    std::fprintf(stderr, "libgff consumer test: %d/%d check(s) failed\n", g_failures, g_checks);
    return 1;
}
