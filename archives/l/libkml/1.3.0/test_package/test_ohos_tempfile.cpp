// test_ohos_tempfile.cpp — HarmonyOS-specific consumer test for libkml 1.3.0.
//
// Exercises the OHOS-adapted temporary-file path through the libkml public
// API (kmlbase::File::CreateNewTempFile / kmlbase::TempFile::CreateTempFile):
// on HarmonyOS PC the system /tmp is read-only, so the adapted
// file_posix.cc honors $TMPDIR and returns a failure path instead of
// crashing. This test verifies that:
//   1) a temp file can actually be created under a writable temp dir,
//   2) the created temp file is writable/readable (the R03 filesystem
//      write-failure cases), and
//   3) TempFile::CreateTempFile returns a non-NULL object (the R03
//      TestCreateFromParseOfKmz null-deref case).
// Returns 0 on success, non-zero otherwise.

#include <cstdio>
#include <string>

#include "kml/base/file.h"
#include "kml/base/tempfile.h"

int main() {
  // 1) CreateNewTempFile must succeed under a writable temp dir.
  std::string tempfile_path;
  if (!kmlbase::File::CreateNewTempFile(&tempfile_path)) {
    return 1;
  }
  if (tempfile_path.empty() || tempfile_path[0] != '/') {
    return 2;
  }

  // 2) The temp file must be writable and readable back.
  const std::string payload("ohos-tempfile-write-check");
  if (!kmlbase::File::WriteStringToFile(payload, tempfile_path)) {
    return 3;
  }
  std::string readback;
  if (!kmlbase::File::ReadFileToString(tempfile_path, &readback)) {
    return 4;
  }
  if (readback != payload) {
    return 5;
  }

  // 3) TempFile::CreateTempFile must return a non-NULL object and its file
  //    must exist (guards the R03 null-deref crash path).
  kmlbase::TempFilePtr tempfile = kmlbase::TempFile::CreateTempFile();
  if (tempfile.get() == NULL) {
    return 6;
  }
  if (tempfile->name().empty()) {
    return 7;
  }
  if (!kmlbase::File::Exists(tempfile->name())) {
    return 8;
  }

  // 4) Cleanup: delete the temp files we created.
  if (!kmlbase::File::Delete(tempfile_path)) {
    return 9;
  }
  if (!kmlbase::File::Delete(tempfile->name())) {
    return 10;
  }

  return 0;
}