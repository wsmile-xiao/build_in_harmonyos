// Consumer test for libosmpbf 1.6.1 — 7 real API assertions (R34).
//
// Covers the installed C++ API end to end without any test data file:
//   1. OSMPBF_VERSION macro is non-empty
//   2. max_blob_header_size == 64 KiB
//   3. max_uncompressed_blob_size == 32 MiB
//   4. lonlat_resolution == 1e9
//   5. BlobHeader serialize/parse round-trip (type + datasize)
//   6. Blob raw-field round-trip
//   7. PrimitiveBlock (stringtable + bbox) + HeaderBlock round-trip
//
// Any failure prints "FAIL ..." to stderr and exits non-zero; success
// prints "ALL CHECKS PASSED (7/7)".

#include <osmpbf/osmpbf.h>

#include <cstdio>
#include <cstring>
#include <string>

namespace {

int g_passed = 0;
int g_failed = 0;

void check(bool cond, const char *name) {
    if (cond) {
        ++g_passed;
        std::printf("PASS %s\n", name);
    } else {
        ++g_failed;
        std::fprintf(stderr, "FAIL %s\n", name);
    }
}

}  // namespace

int main() {
    // 1. version macro
    {
        const char *v = OSMPBF_VERSION;
        check(v != nullptr && std::strlen(v) > 0, "version-macro-non-empty");
    }

    // 2-4. namespace constants
    check(OSMPBF::max_blob_header_size == 64 * 1024, "max-blob-header-size");
    check(OSMPBF::max_uncompressed_blob_size == 32 * 1024 * 1024,
          "max-uncompressed-blob-size");
    check(OSMPBF::lonlat_resolution == 1000 * 1000 * 1000, "lonlat-resolution");

    // 5. BlobHeader round-trip
    {
        OSMPBF::BlobHeader out;
        out.set_type("OSMHeader");
        out.set_datasize(12345);
        std::string buf;
        bool ok = out.SerializeToString(&buf) && !buf.empty();
        OSMPBF::BlobHeader in;
        ok = ok && in.ParseFromString(buf);
        check(ok && in.type() == "OSMHeader" && in.datasize() == 12345,
              "blobheader-round-trip");
    }

    // 6. Blob raw field round-trip
    {
        OSMPBF::Blob out;
        out.set_raw("hello-osmpbf");
        out.set_raw_size(12);
        std::string buf;
        bool ok = out.SerializeToString(&buf) && !buf.empty();
        OSMPBF::Blob in;
        ok = ok && in.ParseFromString(buf);
        check(ok && in.raw() == "hello-osmpbf" && in.raw_size() == 12,
              "blob-raw-round-trip");
    }

    // 7. PrimitiveBlock + HeaderBlock round-trip
    {
        bool ok = true;
        OSMPBF::PrimitiveBlock block;
        block.set_granularity(100);
        block.set_lat_offset(0);
        block.set_lon_offset(0);
        block.mutable_stringtable()->add_s("OSMHeader");
        block.mutable_stringtable()->add_s("amenity");
        std::string bbuf;
        ok = block.SerializeToString(&bbuf) && !bbuf.empty();
        OSMPBF::PrimitiveBlock block2;
        ok = ok && block2.ParseFromString(bbuf);
        ok = ok && block2.granularity() == 100 &&
             block2.stringtable().s_size() == 2 &&
             block2.stringtable().s(1) == "amenity";

        OSMPBF::HeaderBlock header;
        header.mutable_bbox()->set_left(-1800000000);
        header.mutable_bbox()->set_bottom(-90000000);
        header.mutable_bbox()->set_right(1800000000);
        header.mutable_bbox()->set_top(90000000);
        header.add_required_features("OsmSchema-V0.6");
        header.add_required_features("DenseNodes");
        header.set_writingprogram("libosmpbf-test");
        std::string hbuf;
        ok = ok && header.SerializeToString(&hbuf) && !hbuf.empty();
        OSMPBF::HeaderBlock header2;
        ok = ok && header2.ParseFromString(hbuf);
        ok = ok && header2.bbox().left() == -1800000000 &&
             header2.required_features_size() == 2 &&
             header2.writingprogram() == "libosmpbf-test";
        check(ok, "primitiveblock-headerblock-round-trip");
    }

    std::printf("RESULT: %d passed, %d failed (7 checks)\n", g_passed, g_failed);
    if (g_failed == 0 && g_passed == 7) {
        std::printf("ALL CHECKS PASSED (7/7)\n");
        return 0;
    }
    return 1;
}
