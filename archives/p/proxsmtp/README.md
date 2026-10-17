# proxsmtp/1.10 for HarmonyOS PC

This recipe packages upstream `proxsmtpd` as a native AArch64 executable. It retains ordinary SMTP relay/filter operation and compiles the `IP_TRANSPARENT` code path, but disables Linux capabilities because `libcap` was unavailable on the tested device. Privileged transparent proxy behavior is not runtime-verified. Run it with `-f /path/to/proxsmtpd.conf` and set a writable `TempDirectory` in the configuration.

The bundled `config.sub` comes from the [GNU config project](https://git.savannah.gnu.org/cgit/config.git/plain/config.sub) (2026 revision, SHA-256 `f9a31e9a3f5b7cbeb8d8c3f2015895a51e7222130114c9c363fcbccd78e4bf6b`). The upstream 2009 copy does not recognize AArch64/HarmonyOS. One C patch corrects a one-byte out-of-bounds terminator write on the full-line path. Another logs the target's pointer-valued `pthread_t` without truncating it to an `int`. Neither changes the SMTP protocol logic.

Upstream 1.10 does not ship an automated test suite. The added Conan consumer test checks the packaged binary's version and sends a message through a loopback SMTP backend. This does not exercise privileged transparent interception, filtering scripts, or production network deployment.
