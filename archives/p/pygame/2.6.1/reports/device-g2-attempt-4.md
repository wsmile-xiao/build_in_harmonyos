# HarmonyOS PC G2 attempt 4

- Result archive: `pygame-device-results.tar.gz` received 2026-09-05
- Result archive SHA-256: `742986b27a597a0e55b7cbf5b14ac29da2a96fadad73611f312dd5d5eeebecdf`
- Run ID: `20260905T105823Z-5672`
- G2 exit code: 1

W0 passed all 10 direct dependency checks. The recipe built, signed, repacked,
reinstalled, and exercised the final OHOS wheel. The upstream runner reached
all 1,855 cases with the exact 44-module inventory and reported 1,767 ordinary
passes, 14 expected failures, 73 skips, and one failure:
`mixer_test.ChannelTypeTest.test_queue`.

The failure is at `test/mixer_test.py:861`, immediately after `channel.stop()`.
It is not the earlier assertion after a 400 ms wait. SDL_mixer 2.8.1 sets the
channel idle and then invokes pygame's finished callback; pygame still sees
the queued sound and starts it again. Waiting for that sound to end would
conceal the broken stop behavior.

The final source correction is `patches/0001-src_c-mixer.c.patch`, generated
with `refresh-patch --auto` and dry-run checked against the exact sdist. It
detaches the Python queue under the GIL before public `Mix_HaltChannel`, and
the finished callback acquires the GIL before reading or moving queue state.
The current delivery bundle contains this patch and requires one more OHOS
rerun.

The upstream `ChannelTypeTest.test_queue` is unchanged, including all 11
assertions and immediate post-stop checks. No extra skip or wait is added;
the expected target skip count remains 73. The shared consumer now has 34
assertions, including queue setup, immediate idle state, and queue removal.
