// Consumer test for the mmdb (CCP4 mmdb2) Conan package.
//
// Real public-API usage, not a link-only smoke test:
//   1. parse a deterministic PDB fixture with mmdb::Manager::ReadPDBASCII
//      (inherited from mmdb::Root)
//   2. walk the parsed structure bottom-up through public handles only:
//      mmdb::Root::GetAtomI -> Atom::residue -> Residue::chain ->
//      Chain::GetModel, then query the model and inspect every atom field
//   3. serialize the structure with mmdb::Manager::WritePDBASCII, re-read the
//      generated file and repeat the whole inspection on it
//   4. exercise the residue/element lookup tables (mmdb_tables.h)
//   5. exercise the fixed-column parsers (mmdb_utils.h)
// Every check below contributes to the exit code.
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

#include <mmdb_manager.h>
#include <mmdb_root.h>
#include <mmdb_model.h>
#include <mmdb_chain.h>
#include <mmdb_atom.h>
#include <mmdb_tables.h>
#include <mmdb_utils.h>

static int g_assertions = 0;
static int g_failures = 0;

// NOLINTNEXTLINE(bugprone-macro-parentheses): statement macro on purpose
#define CHECK(cond) do { ++g_assertions; if (!(cond)) { ++g_failures; std::printf("FAIL line %d: %s\n", __LINE__, #cond); } } while (0)

static std::string trimmed(const char *field) {
  std::string s(field);
  size_t b = s.find_first_not_of(" \t");
  if (b == std::string::npos) return std::string();
  size_t e = s.find_last_not_of(" \t");
  return s.substr(b, e - b + 1);
}

// One chain A, one residue ALA, three atoms with known coordinates.
// Columns follow the PDB fixed format: name in 13-16, x/y/z in 31-54,
// occupancy 55-60, temperature factor 61-66, element 77-78.
static const char *kPdbFixture =
    "HEADER    TEST CONSUMER                             01-JAN-95   9999\n"
    "ATOM      1  N   ALA A   1      11.104  13.206  10.562  1.00 20.00           N\n"
    "ATOM      2  CA  ALA A   1      12.104  14.206  11.562  1.00 21.00           C\n"
    "ATOM      3  C   ALA A   1      13.104  15.206  12.562  1.00 22.00           C\n"
    "END\n";

static bool write_text_file(const char *path, const char *content) {
  std::FILE *f = std::fopen(path, "wb");
  if (!f) return false;
  size_t n = std::strlen(content);
  bool ok = (std::fwrite(content, 1, n, f) == n);
  std::fclose(f);
  return ok;
}

static bool file_exists(const char *path) {
  std::FILE *f = std::fopen(path, "rb");
  if (!f) return false;
  std::fclose(f);
  return true;
}

// Everything the inspection below needs, resolved from the public handles.
struct ParsedStructure {
  mmdb::PAtom atom0;
  mmdb::PAtom atom1;
  mmdb::PAtom atom2;
  mmdb::PResidue residue;
  mmdb::PChain chain;
  mmdb::PModel model;
};

// Resolves the parsed hierarchy bottom-up and asserts its contents. Runs both
// on the fixture parse and on the re-read of the file mmdb wrote itself.
static void inspect(mmdb::Manager &file, int expected_atoms) {
  ParsedStructure s;
  s.atom0 = file.GetAtomI(1);
  s.residue = s.atom0 ? s.atom0->residue : 0;
  s.chain = s.residue ? s.residue->chain : 0;
  s.model = s.chain ? s.chain->GetModel() : 0;

  CHECK(s.atom0 != 0);
  CHECK(s.residue != 0);
  CHECK(s.chain != 0);
  CHECK(s.model != 0);
  if (!s.residue || !s.chain || !s.model) return;

  CHECK(s.residue->nAtoms == expected_atoms);
  CHECK(trimmed(s.residue->name) == "ALA");
  CHECK(s.chain->GetNumberOfResidues() == 1);
  CHECK(s.model->GetNumberOfModels() == 1);
  CHECK(s.model->GetNumberOfChains() == 1);
  CHECK(s.model->GetNumberOfAtoms(false) == expected_atoms);
  // Model indices are 0-based (measured: GetChain(0) resolves, GetChain(1)
  // does not) - the round trip has to land back on the very same chain.
  CHECK(s.model->GetChain(0) == s.chain);
  CHECK(s.model->GetChain(1) == 0);

  s.atom1 = s.residue->atom[1];
  s.atom2 = s.residue->atom[2];
  CHECK(s.atom1 != 0 && s.atom2 != 0);
  if (!s.atom1 || !s.atom2) return;
  // All three atoms must belong to the same residue object.
  CHECK(s.atom1->residue == s.residue);
  CHECK(s.atom2->residue == s.residue);

  CHECK(trimmed(s.atom0->name) == "N");
  CHECK(trimmed(s.atom1->name) == "CA");
  CHECK(trimmed(s.atom2->name) == "C");
  CHECK(std::fabs(s.atom0->x - 11.104) < 0.001);
  CHECK(std::fabs(s.atom0->y - 13.206) < 0.001);
  CHECK(std::fabs(s.atom0->z - 10.562) < 0.001);
  CHECK(std::fabs(s.atom1->x - 12.104) < 0.001);
  CHECK(std::fabs(s.atom2->z - 12.562) < 0.001);
  CHECK(std::fabs(s.atom0->occupancy - 1.0) < 0.001);
  CHECK(std::fabs(s.atom0->tempFactor - 20.0) < 0.001);
  CHECK(std::fabs(s.atom2->tempFactor - 22.0) < 0.001);
  CHECK(s.atom0->serNum == 1);
  CHECK(s.atom2->serNum == 3);
  CHECK(trimmed(s.atom0->element) == "N");
  CHECK(trimmed(s.atom1->element) == "C");
}

int main() {
  const char *fixture = "mmdb_consumer_fixture.pdb";
  const char *written = "mmdb_consumer_written";

  CHECK(write_text_file(fixture, kPdbFixture));

  // ---------- 1. read a PDB coordinate file through the public API ----------
  mmdb::Manager file;
  mmdb::ERROR_CODE read_code = file.ReadPDBASCII(fixture);
  CHECK(read_code == mmdb::Error_Ok);
  std::printf("ReadPDBASCII returned %d\n", (int)read_code);

  // ---------- 2. inspect the parsed structure ----------
  inspect(file, 3);

  // ---------- 3. write it back out and read the generated file again -------
  mmdb::ERROR_CODE write_code = file.WritePDBASCII(written);
  CHECK(write_code == mmdb::Error_Ok);
  std::string roundtrip;
  const char *candidates[] = {
      "mmdb_consumer_written.pdb", "mmdb_consumer_written.ent",
      "mmdb_consumer_written",     "mmdb_consumer_written.pdb1",
      "mmdb_consumer_written.ent1"};
  for (int i = 0; i < 5; ++i) {
    if (file_exists(candidates[i])) { roundtrip = candidates[i]; break; }
  }
  CHECK(!roundtrip.empty());
  if (!roundtrip.empty()) {
    std::printf("file written by mmdb: %s\n", roundtrip.c_str());
    mmdb::Manager reread;
    mmdb::ERROR_CODE again = reread.ReadPDBASCII(roundtrip.c_str());
    CHECK(again == mmdb::Error_Ok);
    inspect(reread, 3);
  }

  // ---------- 4. residue and element lookup tables ----------
  CHECK(mmdb::isAminoacid("ALA"));
  CHECK(!mmdb::isAminoacid("HEM"));
  CHECK(mmdb::isSolvent("HOH"));
  CHECK(!mmdb::isSolvent("ALA"));
  CHECK(mmdb::isDNARNA("DA") == 1);
  CHECK(mmdb::isDNARNA("ALA") == 0);
  mmdb::realtype c_weight = mmdb::getMolecWeight("C");
  CHECK(c_weight > 11.0 && c_weight < 13.0);
  CHECK(mmdb::getCovalentRadius("C") > 0.0);
  CHECK(mmdb::getElementNo("C") > 0);
  CHECK(mmdb::getElementNo("N") > mmdb::getElementNo("C"));
  CHECK(mmdb::getMolecWeight("N") > mmdb::getMolecWeight("C"));
  char one_letter = 63;
  mmdb::Get1LetterCode("ALA", one_letter);
  CHECK(std::string(1, one_letter) == "A");
  CHECK(mmdb::GetAAPIndex("ALA") != mmdb::GetAAPIndex("GLY"));
  mmdb::realtype hydropathy = mmdb::GetAAHydropathy("ALA");
  CHECK(hydropathy >= -4.5 && hydropathy <= 4.5);

  // ---------- 5. fixed-column parsers ----------
  int parsed_int = 0;
  CHECK(mmdb::GetInteger(parsed_int, "  42", 4));
  CHECK(parsed_int == 42);
  mmdb::realtype parsed_real = 0.0;
  CHECK(mmdb::GetReal(parsed_real, " 3.250", 6));
  CHECK(std::fabs(parsed_real - 3.25) < 0.0001);
  char field[8];
  std::memset(field, 32, sizeof(field));
  mmdb::PutInteger(field, 7, 4);
  CHECK(std::memcmp(field, "   7", 4) == 0);

  std::printf("mmdb consumer test: %d assertions, %d failures\n",
              g_assertions, g_failures);
  if (g_failures != 0) return 1;
  std::printf("MMDB_CONSUMER_OK\n");
  return 0;
}
