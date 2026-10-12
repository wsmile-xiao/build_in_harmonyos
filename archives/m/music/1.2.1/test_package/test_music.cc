// Consumer test for MUSIC 1.2.1: compiled and linked as a user of libmusic
// against MPI, then launched on two ranks.  Every check below is a behaviour
// assertion, not a presence check.
#include <mpi.h>

#include <cstdio>
#include <string>

#include "music/configuration.hh"
#include "music/predict_rank.hh"

namespace {

int failures = 0;

void check(bool condition, const char* what) {
  std::printf("%s %s\n", condition ? "PASS" : "FAIL", what);
  if (!condition)
    ++failures;
}

}  // namespace

int main(int argc, char** argv) {
  // predictRank() is documented as the pre-MPI_Init rank guess: query it first.
  const int predicted = MUSIC::predictRank(argc, argv);

  MPI_Init(&argc, &argv);
  int rank = -1;
  int size = -1;
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  MPI_Comm_size(MPI_COMM_WORLD, &size);

  std::printf("MUSIC_CONSUMER rank=%d size=%d predictRank=%d\n", rank, size, predicted);
  std::fflush(stdout);

  check(size == 2, "world size is 2 (real multi-rank launch, not a fallback)");
  check(predicted == rank, "predictRank before MPI_Init agrees with MPI_Comm_rank");

  MUSIC::Configuration config;

  config.insert("np", "3");
  int np = 0;
  check(config.lookup("np", &np) && np == 3, "int option round-trip");

  config.insert("stoptime", "1.5");
  double stoptime = 0.0;
  check(config.lookup("stoptime", &stoptime) && stoptime == 1.5, "double option round-trip");

  config.insert("datafile", "x.dat");
  std::string datafile;
  check(config.lookup("datafile", &datafile) && datafile == "x.dat", "string option round-trip");

  config.insert("verbose", "true");
  bool verbose = false;
  check(config.lookup("verbose", &verbose) && verbose, "bool option round-trip (boolalpha)");

  check(config.lookup("np"), "existence lookup hits a stored key");
  int absent = 0;
  check(!config.lookup("no_such_key", &absent), "lookup of an absent key returns false");

  config.insert("dup", "1");
  config.insert("dup", "2");
  int dup = 0;
  check(config.lookup("dup", &dup) && dup == 1, "insert keeps the first value");

  MUSIC::Configuration::ConfigDict dict;
  dict["alpha"] = "42";
  config.setDict(dict);
  int alpha = 0;
  check(config.lookup("alpha", &alpha) && alpha == 42, "setDict applies the given map");
  check(!config.lookup("np", &np), "setDict replaces rather than merges the old map");
  check(config.getDict().size() == 1, "getDict reflects setDict");

  config.resetDict();
  check(config.getDict().empty(), "resetDict clears the map");
  check(!config.lookup("alpha", &alpha), "keys are gone after resetDict");

  std::printf("MUSIC_CONSUMER rank=%d failures=%d checks=13\n", rank, failures);
  std::fflush(stdout);

  MPI_Finalize();
  return failures == 0 ? 0 : 1;
}
