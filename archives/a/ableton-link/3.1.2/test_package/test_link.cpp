// test_package for ableton-link 3.1.2 — exercises the real public API.
// Constructs an ableton::Link instance, toggles enable, changes tempo via
// SessionState and verifies the values round-trip.
#include <ableton/Link.hpp>

#include <chrono>
#include <cmath>
#include <cstdio>

namespace
{

int g_failures = 0;

void check(bool cond, const char* name)
{
  if (cond) {
    std::printf("PASS: %s\n", name);
  } else {
    std::printf("FAIL: %s\n", name);
    ++g_failures;
  }
}

} // namespace

int main()
{
  using namespace std::chrono;

  ableton::Link link(120.0);

  // 1. A fresh Link instance is disabled.
  check(!link.isEnabled(), "new Link is disabled");

  // 2. Enabling the link is observable through isEnabled().
  link.enable(true);
  check(link.isEnabled(), "Link is enabled after enable(true)");

  // 3. Tempo set through the session state round-trips.
  const auto initial_tempo = link.captureAppSessionState();
  const auto quantum = 4.0;
  const auto bpm = 140.0;
  auto initial = initial_tempo;
  initial.setTempo(bpm, microseconds(0));
  link.commitAppSessionState(initial);

  const auto after = link.captureAppSessionState();
  check(std::fabs(after.tempo() - bpm) < 0.01, "tempo round-trips after commit");

  // 4. Beat grid helpers: beatAtTime/timeAtBeat are consistent.
  const auto beat = after.beatAtTime(microseconds(0), quantum);
  const auto time = after.timeAtBeat(beat, quantum);
  check(time == microseconds(0), "beatAtTime/timeAtBeat consistent at origin");

  // 5. A local instance has no peers.
  check(link.numPeers() == 0, "numPeers is 0 on a fresh instance");

  // 6. Disabling is observable too.
  link.enable(false);
  check(!link.isEnabled(), "Link is disabled after enable(false)");

  std::printf("%s\n", g_failures == 0 ? "ALL TESTS PASSED" : "TESTS FAILED");
  return g_failures == 0 ? 0 : 1;
}
