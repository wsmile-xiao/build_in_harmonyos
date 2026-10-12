/* srf consumer test (R34: exercises the real libsrf API on top of
 * io_lib's ZTR layer) — same flow as upstream test/testWrite.cc +
 * test/testRead.cc combined into one round-trip:
 *   SRF_create_read -> SRF_output_ztr -> SRF_Container::write +
 *   SRF_ReadSet::write -> reopen -> firstReadSet/getRead.
 * Full data path through real SRF file I/O — not print-only. */
#include <SRF_util.hh>
#include <SRF_File.hh>
#include <SRF_Container.hh>
#include <SRF_ReadSet.hh>
#include <SRF_Read.hh>

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

static std::string to_str(int v) {
    std::ostringstream os;
    os << v;
    return os.str();
}

int main() {
    int failures = 0;
    const char *path = "consumer_roundtrip.srf";
    const char *seqIn =
        "8 100 293 551 CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCACC";

    /* ---- Phase 1: write (upstream testWrite.cc flow) ---- */
    {
        SRF_File file(path, SRF_File::openTypeWrite);
        std::fstream &out = file.getFile();

        SRF_Container container;
        container.setup("consumerTest", "0.1");
        container.write(out);

        SRF_ReadSet readSet;
        readSet.setup("consumerTest", "");

        std::vector<SRF_BasePrb> prbs;  /* empty: no quality prbs */
        std::vector<ztr_t> ztrBlobs;
        std::vector<std::string> readIds;

        std::istringstream in(seqIn);
        int a, b, c, d;
        std::string bases;
        int idCounter = 0;
        while (in >> a >> std::skipws >> b >> std::skipws >> c
                  >> std::skipws >> d >> std::skipws >> bases) {
            Read *read = SRF_create_read(bases.c_str(), prbs);
            ztr_t *ztr = SRF_output_ztr(read);
            ztrBlobs.push_back(*ztr);
            readIds.push_back(to_str(idCounter++));
            read_deallocate(read);
        }

        if (ztrBlobs.empty()) {
            std::fprintf(stderr, "FAIL: no ztr blobs created\n");
            return 1;
        }
        if (!readSet.write(out, ztrBlobs, readIds)) {
            std::fprintf(stderr, "FAIL: readSet.write\n");
            return 1;
        }
    }

    /* ---- Phase 2: read back (upstream testRead.cc flow) ---- */
    {
        SRF_File file(path, SRF_File::openTypeRead);
        SRF_Container *container = file.getCurrentContainer();
        if (!container) {
            std::fprintf(stderr, "FAIL: no container\n");
            return 1;
        }
        SRF_ReadSet *readSet = container->firstReadSet(file.getFile());
        if (!readSet) {
            std::fprintf(stderr, "FAIL: no readSet\n");
            return 1;
        }
        int nreads = 0;
        SRF_Read *read = NULL;
        while ((read = readSet->getRead(file.getFile())) != NULL) {
            nreads++;           /* real ZTR parse happens inside getRead */
            delete read;
        }
        if (nreads < 1) {
            std::fprintf(stderr, "FAIL: 0 reads parsed back\n");
            failures++;
        } else {
            std::printf("PASS: srf roundtrip (reads=%d)\n", nreads);
        }
        delete readSet;
    }

    if (failures) return 1;
    return 0;
}
