/* Consumer test for libe-book 0.1.4.
 *
 * Exercises the installed package through its public API exactly the way the
 * upstream conversion tools do (src/conv/text/ebook2text.cpp): construct a
 * stream, ask EBOOKDocument::isSupported for a verdict, then parse into a
 * librevenge::RVNGTextTextGenerator and assert on the text that comes out.
 * The positive case is a real PalmDoc (PDB container, type "TEXt", creator
 * "REAd", one uncompressed text record) built byte by byte in this file, so
 * no test corpus is needed.
 *
 * Verdict is by exit code: any failed assertion prints and returns 1.
 */

#include <cstdio>
#include <cstring>
#include <string>

#include <librevenge/librevenge.h>
#include <librevenge-generators/librevenge-generators.h>
#include <librevenge-stream/librevenge-stream.h>

#include <libe-book/libe-book.h>

namespace
{

int g_failures = 0;

void check(bool condition, const char *what)
{
  if (condition)
  {
    std::printf("ok: %s\n", what);
  }
  else
  {
    std::printf("FAIL: %s\n", what);
    ++g_failures;
  }
}

void be16(std::string &out, unsigned value)
{
  out.push_back(static_cast<char>((value >> 8) & 0xff));
  out.push_back(static_cast<char>(value & 0xff));
}

void be32(std::string &out, unsigned long value)
{
  out.push_back(static_cast<char>((value >> 24) & 0xff));
  out.push_back(static_cast<char>((value >> 16) & 0xff));
  out.push_back(static_cast<char>((value >> 8) & 0xff));
  out.push_back(static_cast<char>(value & 0xff));
}

/* Minimal but genuine PalmDoc: PDB header (78 bytes) + record list (2
 * entries) + PalmDoc header (16 bytes, uncompressed) + one text record. */
std::string makePalmDoc(const std::string &text)
{
  std::string pdb;
  const std::string name = "libe-book-test";
  pdb.append(name);
  pdb.append(32 - name.size(), '\0');
  be16(pdb, 0);           // attributes
  be16(pdb, 0);           // version
  be32(pdb, 0);           // created
  be32(pdb, 0);           // modified
  be32(pdb, 0);           // backup
  be32(pdb, 0);           // modificationNumber
  be32(pdb, 0);           // appInfoID
  be32(pdb, 0);           // sortInfoID
  pdb.append("TEXt");     // type
  pdb.append("REAd");     // creator
  be32(pdb, 2);           // uniqueIDseed
  be32(pdb, 0);           // nextRecordListID
  be16(pdb, 2);           // numRecords

  std::string docHeader;
  be16(docHeader, 1);                        // wVersion
  be16(docHeader, 1);                        // wCompression: 1 = none
  be32(docHeader, text.size());              // text length
  be16(docHeader, 1);                        // text record count
  be16(docHeader, 4096);                     // record size
  be32(docHeader, text.size());              // current position

  const std::size_t listEnd = pdb.size() + 2 * 8;
  const std::size_t docHeaderOffset = listEnd;
  const std::size_t textOffset = docHeaderOffset + docHeader.size();
  // record 0: the PalmDoc header
  be32(pdb, docHeaderOffset);
  pdb.push_back('\0');                       // attributes
  pdb.append(3, '\0');                       // uniqueID
  // record 1: the text
  be32(pdb, textOffset);
  pdb.push_back('\0');
  pdb.append(3, '\0');

  pdb.append(docHeader);
  pdb.append(text);
  return pdb;
}

bool writeFile(const char *path, const std::string &data)
{
  FILE *file = std::fopen(path, "wb");
  if (!file)
    return false;
  const bool ok = data.empty() ||
                  std::fwrite(data.data(), 1, data.size(), file) == data.size();
  return std::fclose(file) == 0 && ok;
}

const char *const kPalmDocPath = "libe_book_smoke.pdb";
const char *const kJunkPath = "libe_book_junk.bin";

} // anonymous namespace

int main()
{
  using namespace libebook;

  const std::string payload = "HarmonyOS PC libe-book smoke test.";
  const std::string palmdoc = makePalmDoc(payload);
  const std::string junk = "this is not an e-book, just plain text\n";

  check(writeFile(kPalmDocPath, palmdoc), "PalmDoc fixture written");
  check(writeFile(kJunkPath, junk), "junk fixture written");

  // ── positive: a real PalmDoc is detected and parses ──────────────────
  {
    librevenge::RVNGFileStream input(kPalmDocPath);
    EBOOKDocument::Type type = EBOOKDocument::TYPE_UNKNOWN;
    const EBOOKDocument::Confidence confidence =
      EBOOKDocument::isSupported(&input, &type);
    check(confidence == EBOOKDocument::CONFIDENCE_EXCELLENT ||
          confidence == EBOOKDocument::CONFIDENCE_WEAK,
          "isSupported recognizes the PalmDoc container");
    check(type == EBOOKDocument::TYPE_PALMDOC,
          "detected type is TYPE_PALMDOC");

    librevenge::RVNGString text;
    librevenge::RVNGTextTextGenerator generator(text, false);
    const EBOOKDocument::Result result =
      EBOOKDocument::parse(&input, &generator, EBOOKDocument::TYPE_PALMDOC);
    check(result == EBOOKDocument::RESULT_OK, "parse() succeeds");
    check(std::strstr(text.cstr(), payload.c_str()) != nullptr,
          "parsed text carries the original payload");
  }

  // ── negative: plain text is not an e-book ────────────────────────────
  {
    librevenge::RVNGFileStream input(kJunkPath);
    EBOOKDocument::Type type = EBOOKDocument::TYPE_UNKNOWN;
    const EBOOKDocument::Confidence confidence =
      EBOOKDocument::isSupported(&input, &type);
    check(confidence == EBOOKDocument::CONFIDENCE_NONE,
          "isSupported rejects plain text");
    check(type == EBOOKDocument::TYPE_UNKNOWN,
          "rejected stream is not classified");

    librevenge::RVNGString text;
    librevenge::RVNGTextTextGenerator generator(text, false);
    const EBOOKDocument::Result result =
      EBOOKDocument::parse(&input, &generator, type);
    check(result != EBOOKDocument::RESULT_OK,
          "parse() fails for an unsupported stream");
  }

  // ── negative: the null contract ──────────────────────────────────────
  check(EBOOKDocument::isSupported(nullptr) == EBOOKDocument::CONFIDENCE_NONE,
        "isSupported(nullptr) returns CONFIDENCE_NONE");

  std::remove(kPalmDocPath);
  std::remove(kJunkPath);

  if (g_failures)
  {
    std::printf("%d check(s) failed\n", g_failures);
    return 1;
  }
  std::printf("all checks passed\n");
  return 0;
}

/* vim:set shiftwidth=2 softtabstop=2 expandtab: */
