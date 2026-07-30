# libkate 0.4.3 adaptation notes

The recipe uses the immutable Xiph release and the upstream Autotools build.
The only source patch extends the bundled GNU `config.sub` whitelist for the
canonical `linux-ohos` target.

CI uses the same native-OHOS profile for host and build, but the Worker cannot
execute unsigned Autoconf probes and the release's `config.guess` temp-file
probe is fragile there. The recipe therefore supplies an OHOS `--host` triplet
and, on native-OHOS workers, a GNU `--build` triplet such as
`aarch64-unknown-linux-gnu`. Keeping `--build` different from `--host` preserves
Autoconf cross-compilation mode and leaves runtime checks to the HarmonyOS PC
emulator.
CI build #11231 additionally showed that the OHOS Worker can run with a
restrictive umask: `config.status` created `conf*/subs1.awk` without sufficient
permissions and failed with `Permission denied`. The Autotools build path now
patches the generated `configure` script before running it, replacing
Autoconf's embedded `umask 077` temp-directory creation with `umask 022` and
`${TMPDIR:-.}`-backed `confXXXXXX` directories. The process umask is still kept
at `022` for OHOS configure/build steps, keeping generated helper files
accessible without changing the source archive or dependency set.

For Windows-hosted OHOS cross builds, the recipe exports a CMake description
of the same upstream library sources because the release's shell-based
Autotools flow cannot run on that host. Native Linux validation continues to
use Autotools and executes the complete upstream `make check` suite.

Both published dependencies are explicit: `libogg/1.3.5` provides Ogg
integration and `libpng/1.6.58` enables the PNG stream checks. Documentation
and the optional KateDJ GUI are not required for the library package.

The upstream `make check` inventory contains:

- 6 Automake program tests (`bitwise`, `check_sizes`, `language`, `metadata`,
  `overflow`, and `text`);
- 3 static/source check groups;
- 11 SRT, 11 LRC, and 19 Kate stream round trips.

That is 50 logical groups, all retained. The added consumer exercises public
version, information, language, and fault-return APIs.
