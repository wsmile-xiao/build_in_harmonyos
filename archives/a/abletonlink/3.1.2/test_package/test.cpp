// test_package consumer test for abletonlink 3.1.2.
// Exercises the real public API of the header-only Ableton Link library:
// construction, tempo get/set via SessionState, enable/isEnabled, numPeers
// and beatAtTime.
#include <ableton/Link.hpp>

#include <chrono>
#include <cmath>
#include <cstdio>

int main()
{
  using namespace std::chrono;

  ableton::Link link(120.0);

  // 1. Initial tempo as passed to the constructor.
  auto state = link.captureAppSessionState();
  if (std::fabs(state.tempo() - 120.0) > 1e-6)
  {
    std::printf("FAIL: initial tempo=%f, expected 120.0\n", state.tempo());
    return 1;
  }

  // 2. setTempo round-trips through the session state.
  state.setTempo(90.0, microseconds{0});
  if (std::fabs(state.tempo() - 90.0) > 1e-6)
  {
    std::printf("FAIL: tempo after setTempo=%f, expected 90.0\n", state.tempo());
    return 2;
  }

  // 3. enable()/isEnabled().
  if (link.isEnabled())
  {
    std::printf("FAIL: Link should start disabled\n");
    return 3;
  }
  link.enable(true);
  if (!link.isEnabled())
  {
    std::printf("FAIL: Link did not enable\n");
    return 4;
  }

  // 4. A fresh instance has no peers.
  if (link.numPeers() != 0)
  {
    std::printf("FAIL: numPeers=%zu, expected 0\n", link.numPeers());
    return 5;
  }

  // 5. beatAtTime returns a finite beat value.
  auto beat = state.beatAtTime(microseconds{0}, 4.0);
  if (!std::isfinite(beat))
  {
    std::printf("FAIL: beatAtTime=%f is not finite\n", beat);
    return 6;
  }

  link.enable(false);
  std::printf("abletonlink test_package OK: tempo=%f beat=%f\n", state.tempo(), beat);
  return 0;
}
