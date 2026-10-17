#include <snd.h>
#include <cstdio>

// Real consumer test: exercises the packaged libsnd static library API.
int main() {
  // FlipFlop: deterministic two-state machine.
  snd::FlipFlop ff(false);
  bool a = ff.state;
  bool b = ff.tick();
  bool c = ff.tick();
  // Denormal support check.
  bool den = snd::isDenormal(1.0);

  std::printf("libsnd consumer test: ff=%d->%d->%d den=%d\n", a ? 1 : 0,
              b ? 1 : 0, c ? 1 : 0, den ? 1 : 0);

  if (a == b || b == c) return 1;  // FlipFlop must alternate states
  if (den) return 2;               // 1.0 must not be denormal
  return 0;
}