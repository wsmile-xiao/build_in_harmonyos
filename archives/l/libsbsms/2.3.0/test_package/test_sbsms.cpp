// test_package/test_sbsms.cpp — consumer-side functional test for libsbsms.
//
// Upstream 2.3.0 ships no test suite, so this program is the package's only
// executable evidence.  It links against the installed package through the
// Conan-generated CMake config and drives the public API end to end:
//
//   SBSMSQuality / SBSMSQualityStandard   -> shipped quality table fingerprint
//   Slide                                 -> identity / constant rate & pitch
//   SBSMSInterfaceSliding (subclassed)    -> input feed contract (samples())
//   SBSMS::read                           -> analysis + synthesis round trip
//
// The round trip is checked *functionally*, not merely for non-emptiness: a
// 440 Hz mono tone is pushed through and the dominant frequency of the output
// is estimated by zero crossings.  Identity must preserve 440 Hz, a x2 pitch
// slide must move it to ~880 Hz, and a x2 rate slide must preserve 440 Hz while
// halving the output length.

#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>

#include "sbsms.h"

using namespace _sbsms_;

namespace {

const double kPi = 3.14159265358979323846;
const int kRate = 44100;
const double kToneHz = 440.0;

int g_checks = 0;
int g_failed = 0;

void tally(bool ok) {
  ++g_checks;
  if (!ok) ++g_failed;
}

void check(bool ok, const char *what) {
  std::printf("  %s %s\n", ok ? "[ok]  " : "[FAIL]", what);
  tally(ok);
}

void checkEqL(const char *what, long long got, long long want) {
  const bool ok = (got == want);
  std::printf("  %s %s: got=%lld want=%lld\n", ok ? "[ok]  " : "[FAIL]", what, got, want);
  tally(ok);
}

void checkNear(const char *what, double got, double want, double tol) {
  const bool ok = std::fabs(got - want) <= tol;
  std::printf("  %s %s: got=%.6g want=%.6g tol=%.6g\n",
              ok ? "[ok]  " : "[FAIL]", what, got, want, tol);
  tally(ok);
}

// Feeds a mono 440 Hz tone through the SBSMSInterface contract.
class ToneFeed : public SBSMSInterfaceSliding {
 public:
  ToneFeed(Slide *rate, Slide *pitch, SBSMSQuality *quality, SampleCountType total)
      : SBSMSInterfaceSliding(rate, pitch, true, total, 0, quality),
        pos_(0),
        total_(total) {}

  long samples(audio *buf, long n) override {
    long written = 0;
    for (long i = 0; i < n && pos_ < total_; ++i, ++pos_) {
      buf[i][0] = 0.5f * (float)std::sin(2.0 * kPi * kToneHz * (double)pos_ / kRate);
      buf[i][1] = 0.0f;
      ++written;
    }
    return written;
  }

 private:
  SampleCountType pos_;
  SampleCountType total_;
};

struct Result {
  std::vector<float> mono;   // channel 0 samples produced
  SampleCountType want = 0;  // iface.getSamplesToOutput()
  bool error = false;        // SBSMS::getError() != SBSMSErrorNone
};

// Drives one scenario exactly the way the upstream example does: read
// getFrameSize() frames at a time until getSamplesToOutput() is reached.
Result runScenario(SlideType rateType, float rateValue,
                   SlideType pitchType, float pitchValue) {
  SBSMSQuality quality(&SBSMSQualityStandard);
  Slide rateSlide(rateType, rateValue);
  Slide pitchSlide(pitchType, pitchValue);
  ToneFeed iface(&rateSlide, &pitchSlide, &quality, kRate);
  SBSMS sbsms(1, &quality, true);

  Result result;
  result.want = iface.getSamplesToOutput();
  result.error = (sbsms.getError() != SBSMSErrorNone);

  const long block = quality.getFrameSize();
  std::vector<float> raw((size_t)block * 2, 0.0f);
  audio *buf = reinterpret_cast<audio *>(raw.data());

  SampleCountType pos = 0;
  while (pos < result.want) {
    std::memset(buf, 0, sizeof(audio) * (size_t)block);
    const long got = sbsms.read(&iface, buf, block);
    if (got <= 0) break;
    for (long i = 0; i < got; ++i) result.mono.push_back(buf[i][0]);
    pos += got;
  }
  return result;
}

bool allFinite(const std::vector<float> &mono) {
  for (size_t i = 0; i < mono.size(); ++i) {
    if (!std::isfinite(mono[i])) return false;
  }
  return true;
}

double energy(const std::vector<float> &mono) {
  double e = 0.0;
  for (size_t i = 0; i < mono.size(); ++i) e += (double)mono[i] * mono[i];
  return e;
}

double peak(const std::vector<float> &mono) {
  double p = 0.0;
  for (size_t i = 0; i < mono.size(); ++i) {
    const double a = std::fabs((double)mono[i]);
    if (a > p) p = a;
  }
  return p;
}

// Dominant frequency estimate from zero crossings over [from, from + n).
double estimateHz(const std::vector<float> &mono, size_t from, size_t n) {
  if (from + n > mono.size() || n < 2) return -1.0;
  int crossings = 0;
  for (size_t i = from + 1; i < from + n; ++i) {
    if ((mono[i - 1] <= 0.0f) != (mono[i] <= 0.0f)) ++crossings;
  }
  return (crossings / 2.0) / ((double)n / kRate);
}

// Zero-crossing estimate over the middle half of a signal.
double estimateHzMid(const std::vector<float> &mono) {
  const size_t quarter = mono.size() / 4;
  return estimateHz(mono, quarter, mono.size() / 2);
}

void report(const char *label, const Result &r) {
  std::printf("%s: want=%lld produced=%zu peak=%.5g energy=%.6g\n", label,
              (long long)r.want, r.mono.size(), peak(r.mono), energy(r.mono));
}

}  // namespace

int main() {
  // ── 1. Package fingerprint: the shipped quality table is the real 2.3.0 one,
  //       the library linked is not an unrelated same-named artifact.
  std::printf("[1] shipped quality table / API values\n");
  checkEqL("SBSMSQualityStandard.bands", SBSMSQualityStandard.bands, 8);
  checkEqL("SBSMSQualityStandard.H", SBSMSQualityStandard.H, 3);
  checkEqL("SBSMSQualityStandard.N[0]", SBSMSQualityStandard.N[0], 512);
  checkEqL("SBSMSQualityStandard.N2[0]", SBSMSQualityStandard.N2[0], 512);
  checkEqL("SBSMSQualityStandard.res[0]", SBSMSQualityStandard.res[0], 1);

  SBSMSQuality quality(&SBSMSQualityStandard);
  checkEqL("quality.getFrameSize()", quality.getFrameSize(), 384);
  checkEqL("quality.getMaxPresamples()", quality.getMaxPresamples(), 19584);

  Slide identity(SlideIdentity);
  checkNear("SlideIdentity.getTotalStretch()", identity.getTotalStretch(), 1.0, 0.0);
  checkNear("SlideIdentity.getRate()", identity.getRate(), 1.0, 0.0);

  // ── 2. Identity round trip: 440 Hz in, 440 Hz out, same length.
  std::printf("[2] identity stretch/pitch (440 Hz -> 440 Hz)\n");
  const Result ident = runScenario(SlideIdentity, 1.0f, SlideIdentity, 1.0f);
  report("  identity", ident);
  check(!ident.error, "SBSMS::getError() == SBSMSErrorNone");
  checkEqL("samplesToOutput", (long long)ident.want, 44100);
  checkEqL("produced samples", (long long)ident.mono.size(), 44160);
  check(allFinite(ident.mono), "output all finite");
  check(energy(ident.mono) > 0.0, "output non-silent");
  checkNear("output peak", peak(ident.mono), 0.5, 0.3);
  checkNear("output frequency Hz", estimateHzMid(ident.mono), kToneHz, 0.05 * kToneHz);

  // ── 3. Pitch shift one octave up: 440 Hz -> ~880 Hz, length unchanged.
  std::printf("[3] pitch x2 (440 Hz -> 880 Hz)\n");
  const Result pitched = runScenario(SlideIdentity, 1.0f, SlideConstant, 2.0f);
  report("  pitch x2", pitched);
  check(!pitched.error, "SBSMS::getError() == SBSMSErrorNone");
  checkEqL("samplesToOutput", (long long)pitched.want, 44100);
  checkEqL("produced samples", (long long)pitched.mono.size(), 44160);
  check(allFinite(pitched.mono), "output all finite");
  checkNear("output frequency Hz", estimateHzMid(pitched.mono), 2.0 * kToneHz,
            0.05 * 2.0 * kToneHz);

  // ── 4. Time stretch x2 (double speed): half the length, pitch preserved.
  std::printf("[4] rate x2 (double speed, pitch preserved)\n");
  const Result faster = runScenario(SlideConstant, 2.0f, SlideIdentity, 1.0f);
  report("  rate x2", faster);
  check(!faster.error, "SBSMS::getError() == SBSMSErrorNone");
  checkEqL("samplesToOutput", (long long)faster.want, 22050);
  checkEqL("produced samples", (long long)faster.mono.size(), 22272);
  check(allFinite(faster.mono), "output all finite");
  checkNear("output frequency Hz", estimateHzMid(faster.mono), kToneHz, 0.05 * kToneHz);

  std::printf("checks=%d failed=%d\n", g_checks, g_failed);
  if (g_failed != 0) {
    std::printf("RESULT: FAIL\n");
    return 1;
  }
  std::printf("RESULT: PASS\n");
  return 0;
}
