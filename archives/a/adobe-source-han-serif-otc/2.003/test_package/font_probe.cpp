#include <dirent.h>
#include <sys/stat.h>

#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
uint16_t be16(const unsigned char* p) {
    return static_cast<uint16_t>((p[0] << 8) | p[1]);
}

uint32_t be32(const unsigned char* p) {
    return (static_cast<uint32_t>(p[0]) << 24) |
           (static_cast<uint32_t>(p[1]) << 16) |
           (static_cast<uint32_t>(p[2]) << 8) |
           static_cast<uint32_t>(p[3]);
}

bool contains_range(uint64_t size, uint64_t offset, uint64_t length) {
    return offset <= size && length <= size - offset;
}

bool ends_with(const std::string& value, const std::string& suffix) {
    return value.size() >= suffix.size() &&
           value.compare(value.size() - suffix.size(), suffix.size(), suffix) == 0;
}

void collect_collections(const std::string& root, std::vector<std::string>& collections) {
    using DirHandle = std::unique_ptr<DIR, int (*)(DIR*)>;
    DirHandle dir(opendir(root.c_str()), closedir);
    if (!dir) {
        throw std::runtime_error("cannot open directory: " + root);
    }
    while (dirent* entry = readdir(dir.get())) {
        const std::string name(entry->d_name);
        if (name == "." || name == "..") {
            continue;
        }
        const std::string path = root + "/" + name;
        struct stat info {};
        if (stat(path.c_str(), &info) != 0) {
            throw std::runtime_error("cannot stat: " + path);
        }
        if (S_ISDIR(info.st_mode)) {
            collect_collections(path, collections);
        } else if (S_ISREG(info.st_mode) && ends_with(name, ".ttc")) {
            collections.push_back(path);
        }
    }
}

std::vector<unsigned char> read_file(const std::string& path) {
    std::ifstream stream(path.c_str(), std::ios::binary | std::ios::ate);
    if (!stream) {
        throw std::runtime_error("cannot read collection: " + path);
    }
    const std::streamoff end = stream.tellg();
    if (end < 0) {
        throw std::runtime_error("cannot determine collection size: " + path);
    }
    const uint64_t size = static_cast<uint64_t>(end);
    if (size > static_cast<uint64_t>(SIZE_MAX)) {
        throw std::runtime_error("collection is too large for this process: " + path);
    }
    stream.seekg(0);
    std::vector<unsigned char> bytes(static_cast<size_t>(size));
    stream.read(reinterpret_cast<char*>(bytes.data()), static_cast<std::streamsize>(size));
    if (!stream) {
        throw std::runtime_error("short read: " + path);
    }
    return bytes;
}

void validate_sfnt_face(
    const std::vector<unsigned char>& bytes,
    uint64_t face_offset,
    const std::string& path,
    uint32_t face_index
) {
    const uint64_t size = bytes.size();
    if (!contains_range(size, face_offset, 12)) {
        throw std::runtime_error("truncated SFNT face " + std::to_string(face_index) + ": " + path);
    }
    const unsigned char* header = bytes.data() + static_cast<size_t>(face_offset);
    const uint32_t signature = be32(header);
    if (signature != 0x00010000u && signature != 0x4f54544fu) {
        throw std::runtime_error("unsupported SFNT signature in face " + std::to_string(face_index) + ": " + path);
    }
    const uint16_t table_count = be16(header + 4);
    const uint64_t directory_size = 12u + static_cast<uint64_t>(table_count) * 16u;
    if (table_count == 0 || !contains_range(size, face_offset, directory_size)) {
        throw std::runtime_error("invalid table directory in face " + std::to_string(face_index) + ": " + path);
    }

    std::set<std::string> tags;
    for (uint16_t index = 0; index < table_count; ++index) {
        const uint64_t record_offset = face_offset + 12u + static_cast<uint64_t>(index) * 16u;
        const unsigned char* record = bytes.data() + static_cast<size_t>(record_offset);
        const std::string tag(reinterpret_cast<const char*>(record), 4);
        const uint64_t table_offset = be32(record + 8);
        const uint64_t table_length = be32(record + 12);
        if (!contains_range(size, table_offset, table_length)) {
            throw std::runtime_error("out-of-bounds table " + tag + " in face " +
                                     std::to_string(face_index) + ": " + path);
        }
        tags.insert(tag);
    }

    const char* required[] = {"name", "cmap", "head", "maxp"};
    for (const char* tag : required) {
        if (tags.count(tag) == 0) {
            throw std::runtime_error(std::string("missing ") + tag + " table in face " +
                                     std::to_string(face_index) + ": " + path);
        }
    }
    if (tags.count("glyf") == 0 && tags.count("CFF ") == 0 && tags.count("CFF2") == 0) {
        throw std::runtime_error("missing glyph outline table in face " +
                                 std::to_string(face_index) + ": " + path);
    }
}

uint32_t validate_collection(const std::string& path, uint32_t expected_faces) {
    const std::vector<unsigned char> bytes = read_file(path);
    const uint64_t size = bytes.size();
    if (size < 12) {
        throw std::runtime_error("truncated TTC header: " + path);
    }
    if (be32(bytes.data()) != 0x74746366u) {
        throw std::runtime_error("missing ttcf signature: " + path);
    }
    const uint32_t version = be32(bytes.data() + 4);
    if (version != 0x00010000u && version != 0x00020000u) {
        throw std::runtime_error("unsupported TTC version: " + path);
    }
    const uint32_t face_count = be32(bytes.data() + 8);
    if (face_count == 0 || face_count != expected_faces) {
        throw std::runtime_error("TTC face count mismatch: expected " +
                                 std::to_string(expected_faces) + ", got " +
                                 std::to_string(face_count) + ": " + path);
    }
    const uint64_t offsets_size = static_cast<uint64_t>(face_count) * 4u;
    if (!contains_range(size, 12, offsets_size)) {
        throw std::runtime_error("truncated TTC face-offset array: " + path);
    }
    std::set<uint32_t> offsets;
    for (uint32_t index = 0; index < face_count; ++index) {
        const uint32_t face_offset = be32(bytes.data() + 12u + static_cast<size_t>(index) * 4u);
        if (!offsets.insert(face_offset).second) {
            throw std::runtime_error("duplicate TTC face offset: " + path);
        }
        validate_sfnt_face(bytes, face_offset, path, index);
    }
    return face_count;
}
}

int main(int argc, char** argv) {
    try {
        if (argc == 3 && std::string(argv[1]) == "--expect-invalid") {
            try {
                validate_collection(argv[2], 5);
            } catch (const std::exception&) {
                std::cout << "PASS: corrupted TTC rejected\n";
                return 0;
            }
            std::cerr << "FAIL: corrupted TTC was accepted\n";
            return 1;
        }
        if (argc != 4) {
            std::cerr << "usage: font_probe <collection-root> <expected-files> <expected-faces-per-file>\n";
            return 2;
        }
        const long expected_files = std::strtol(argv[2], nullptr, 10);
        const long expected_faces = std::strtol(argv[3], nullptr, 10);
        if (expected_files <= 0 || expected_faces <= 0) {
            throw std::runtime_error("expected counts must be positive");
        }
        std::vector<std::string> collections;
        collect_collections(argv[1], collections);
        if (collections.size() != static_cast<size_t>(expected_files)) {
            throw std::runtime_error("collection count mismatch: expected " +
                                     std::to_string(expected_files) + ", got " +
                                     std::to_string(collections.size()));
        }
        uint64_t total_faces = 0;
        for (const std::string& collection : collections) {
            total_faces += validate_collection(collection, static_cast<uint32_t>(expected_faces));
        }
        std::cout << "PASS: parsed " << collections.size() << " TTC files and "
                  << total_faces << " SFNT faces\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
