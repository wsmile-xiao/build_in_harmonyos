#include <osmpbf/osmpbf.h>

#include <cstdio>
#include <cstring>
#include <string>

// R34: 实质依赖被测包——include 公开头文件、使用公开常量、调用 libosmpbf 内
// protobuf 生成类型的 API（强制链接 libosmpbf，而非空壳打印）。
int main() {
    if (std::strcmp(OSMPBF_VERSION, "1.5.0") != 0) {
        std::fprintf(stderr, "unexpected OSMPBF_VERSION: %s\n", OSMPBF_VERSION);
        return 1;
    }
    if (OSMPBF::max_blob_header_size != 64 * 1024) {
        std::fprintf(stderr, "unexpected max_blob_header_size: %d\n",
                     OSMPBF::max_blob_header_size);
        return 2;
    }
    if (OSMPBF::max_uncompressed_blob_size != 32 * 1024 * 1024) {
        std::fprintf(stderr, "unexpected max_uncompressed_blob_size: %d\n",
                     OSMPBF::max_uncompressed_blob_size);
        return 3;
    }

    OSMPBF::BlobHeader header;
    header.set_type("OSMHeader");
    header.set_datasize(42);
    if (header.type() != "OSMHeader" || header.datasize() != 42) {
        std::fprintf(stderr, "BlobHeader setters/getters failed\n");
        return 4;
    }

    // Serialize/parse round-trip — exercises generated code inside libosmpbf.
    std::string wire;
    if (!header.SerializeToString(&wire) || wire.empty()) {
        std::fprintf(stderr, "BlobHeader::SerializeToString failed\n");
        return 5;
    }
    OSMPBF::BlobHeader parsed;
    if (!parsed.ParseFromString(wire)) {
        std::fprintf(stderr, "BlobHeader::ParseFromString failed\n");
        return 6;
    }
    if (parsed.type() != "OSMHeader" || parsed.datasize() != 42) {
        std::fprintf(stderr, "BlobHeader round-trip mismatch\n");
        return 7;
    }

    std::printf("osmpbf consumer API ok version=%s type=%s datasize=%d\n",
                OSMPBF_VERSION, parsed.type().c_str(), parsed.datasize());
    return 0;
}
