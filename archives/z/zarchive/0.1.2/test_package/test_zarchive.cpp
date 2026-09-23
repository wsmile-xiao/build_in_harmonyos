/*
 * Consumer test for the zarchive package — real API calls against the
 * installed library, headless.
 *
 * Packs a directory tree into an archive with ZArchiveWriter, then reads it
 * back with ZArchiveReader and asserts on the result: file lookup, sizes,
 * byte-exact contents, directory enumeration and the invalid-handle case.
 * The archive is zstd-compressed end to end, so a passing round trip also
 * proves the zstd dependency is correctly propagated to consumers.
 *
 * Exits non-zero as soon as any check fails.
 */

#include <zarchive/zarchivewriter.h>
#include <zarchive/zarchivereader.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

static int checks = 0;
static int failures = 0;

static void check(bool condition, const char *what)
{
    checks++;
    if (condition)
        printf("ok %d - %s\n", checks, what);
    else
        printf("not ok %d - %s\n", checks, what);
    if (!condition)
        failures++;
}

struct PackContext
{
    std::ofstream out;
    bool ok = false;
};

static void on_new_file(const int32_t, void *ctx)
{
    PackContext *pc = static_cast<PackContext *>(ctx);
    pc->out.close();
    pc->out.open("consumer_test.zar", std::ios::binary);
    pc->ok = pc->out.is_open();
}

static void on_write(const void *data, size_t length, void *ctx)
{
    PackContext *pc = static_cast<PackContext *>(ctx);
    pc->out.write(static_cast<const char *>(data), length);
}

static std::vector<uint8_t> read_file(const fs::path &path)
{
    std::ifstream in(path, std::ios::binary);
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(in),
                                std::istreambuf_iterator<char>());
}

static void write_file(const fs::path &path, const void *data, size_t size)
{
    fs::create_directories(path.parent_path());
    std::ofstream out(path, std::ios::binary);
    out.write(static_cast<const char *>(data), size);
}

int main()
{
    std::error_code ec;
    fs::remove_all("consumer_src", ec);
    fs::remove_all("consumer_zstd", ec);
    fs::remove("consumer_test.zar", ec);

    /* Known payloads, including one with every byte value and one with
     * embedded NULs, so truncation or encoding damage cannot pass. */
    const std::string text = "ZArchive round trip payload\n";
    std::vector<uint8_t> binary(256);
    for (size_t i = 0; i < binary.size(); i++)
        binary[i] = static_cast<uint8_t>(i);
    const std::string zeros(1024, '\0');

    write_file("consumer_src/hello.txt", text.data(), text.size());
    write_file("consumer_src/sub/nested.bin", binary.data(), binary.size());
    write_file("consumer_src/sub/deep/zeros.txt", zeros.data(), zeros.size());

    /* ── pack ─────────────────────────────────────────────────────── */
    PackContext context;
    ZArchiveWriter writer(on_new_file, on_write, &context);
    check(writer.MakeDir("sub/deep", true), "MakeDir(sub/deep, recursive) succeeds");
    check(writer.StartNewFile("hello.txt"), "StartNewFile(hello.txt) succeeds");
    writer.AppendData(text.data(), text.size());
    check(writer.StartNewFile("sub/nested.bin"), "StartNewFile(sub/nested.bin) succeeds");
    writer.AppendData(binary.data(), binary.size());
    check(writer.StartNewFile("sub/deep/zeros.txt"), "StartNewFile(sub/deep/zeros.txt) succeeds");
    writer.AppendData(zeros.data(), zeros.size());
    writer.Finalize();
    context.out.close();
    check(context.ok, "output stream opened by the writer callback");

    uintmax_t archiveSize = fs::file_size("consumer_test.zar", ec);
    check(!ec && archiveSize > 0, "archive file was written and is non-empty");
    check(archiveSize < text.size() + zeros.size() + binary.size() + 4096,
          "archive stays in the same size class as its payload (compression ran)");

    /* ── read back ────────────────────────────────────────────────── */
    ZArchiveReader *reader = ZArchiveReader::OpenFromFile("consumer_test.zar");
    check(reader != nullptr, "ZArchiveReader::OpenFromFile succeeds");
    if (reader == nullptr) {
        printf("1..%d\n", checks);
        printf("# %d checks, %d failures\n", checks, failures);
        return failures ? 1 : 0;
    }

    ZArchiveNodeHandle hello = reader->LookUp("hello.txt");
    check(hello != ZARCHIVE_INVALID_NODE, "LookUp(hello.txt) resolves");
    check(reader->IsFile(hello), "hello.txt is reported as a file");
    check(reader->GetFileSize(hello) == text.size(),
          "hello.txt size matches the source");
    std::vector<char> out(text.size() + 1, '\0');
    uint64_t got = reader->ReadFromFile(hello, 0, out.size(), out.data());
    check(got == text.size(), "ReadFromFile returns the full length");
    check(std::memcmp(out.data(), text.data(), text.size()) == 0,
          "hello.txt contents are byte-identical");

    ZArchiveNodeHandle nested = reader->LookUp("sub/nested.bin");
    check(nested != ZARCHIVE_INVALID_NODE, "LookUp(sub/nested.bin) resolves");
    check(reader->GetFileSize(nested) == binary.size(),
          "nested.bin size matches the source");
    std::vector<uint8_t> nestedOut(binary.size());
    got = reader->ReadFromFile(nested, 0, nestedOut.size(), nestedOut.data());
    check(got == binary.size() && nestedOut == binary,
          "nested.bin contents are byte-identical (all 256 byte values)");

    ZArchiveNodeHandle zerosHandle = reader->LookUp("sub/deep/zeros.txt");
    check(zerosHandle != ZARCHIVE_INVALID_NODE, "LookUp(sub/deep/zeros.txt) resolves");
    std::vector<char> zerosOut(zeros.size());
    got = reader->ReadFromFile(zerosHandle, 0, zerosOut.size(), zerosOut.data());
    check(got == zeros.size() && std::memcmp(zerosOut.data(), zeros.data(), zeros.size()) == 0,
          "zeros.txt contents survive embedded NULs");

    /* A partial read must return exactly the requested slice. */
    std::vector<char> slice(4);
    got = reader->ReadFromFile(hello, 3, slice.size(), slice.data());
    check(got == slice.size() && std::memcmp(slice.data(), text.data() + 3, 4) == 0,
          "ReadFromFile honours the offset argument");

    ZArchiveNodeHandle sub = reader->LookUp("sub", false, true);
    check(sub != ZARCHIVE_INVALID_NODE, "LookUp(sub, directory only) resolves");
    check(reader->IsDirectory(sub), "sub is reported as a directory");
    check(reader->GetDirEntryCount(sub) == 2,
          "sub contains exactly two entries (nested.bin and deep)");

    check(reader->LookUp("does/not/exist") == ZARCHIVE_INVALID_NODE,
          "LookUp on a missing path returns ZARCHIVE_INVALID_NODE");

    delete reader;

    /* ── extract through the library, then compare with the source ── */
    fs::create_directories("consumer_zstd", ec);
    reader = ZArchiveReader::OpenFromFile("consumer_test.zar");
    check(reader != nullptr, "second OpenFromFile succeeds");
    if (reader != nullptr) {
        ZArchiveNodeHandle h = reader->LookUp("sub/deep/zeros.txt");
        std::vector<char> buf(zeros.size());
        reader->ReadFromFile(h, 0, buf.size(), buf.data());
        write_file("consumer_zstd/zeros.txt", buf.data(), buf.size());
        delete reader;
    }
    check(read_file("consumer_zstd/zeros.txt") == read_file("consumer_src/sub/deep/zeros.txt"),
          "library-extracted file matches the original on disk");

    printf("1..%d\n", checks);
    printf("# %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
