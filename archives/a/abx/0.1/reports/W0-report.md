# abx 0.1 W0 dependency publication report

Date: 2026-08-19

## Required references

Runtime/build inputs derived from `configure.ac`, the GTK3 port, and the Conan
recipe:

- `glib/2.84.0.1`
- `gtk/3.24.38`
- `libsndfile/1.2.2`
- `portaudio/19.7.0`
- `automake/1.18` (build tool)

## Mechanical check

The project-mandated check was run against remote `ohpcd` with an isolated
Conan 2.29.1 home on the HarmonyOS device while holding the global Shadow lock:

```text
/storage/Users/currentUser/ohpc-ci-shadow/w0-abx-20260819T052321Z-1275
```

Each reference used:

```sh
conan download "<reference>" -r=ohpcd --only-recipe
```

Results:

| Reference | Exit | Result |
|---|---:|---|
| `glib/2.84.0.1` | 0 | Published recipe downloaded. |
| `automake/1.18` | 0 | Published recipe downloaded. |
| `gtk/3.24.38` | 1 | Not published; remote returned `system acceleration policy not enabled`. |
| `libsndfile/1.2.2` | 1 | Not published; remote returned `system acceleration policy not enabled`. |
| `portaudio/19.7.0` | 1 | Not published; remote returned `system acceleration policy not enabled`. |
| `abx/0.1` | 1 | No published target recipe observed; recheck before PR. |

The two successful downloads in the same environment prove that the remote and
anonymous access were working. Repository inspection independently found no
published recipe for the three failed direct dependencies on `origin/main`.
AtomGit PRs #5578, #5739, and #5782 remain open; each has passed its independent
device/Shadow validation but has not been merged or published.

## Integration diagnostic

After W0 failed, a separate isolated Conan home was populated from read-only
copies of the already validated dependency PR caches. A direct `conan create`
for abx then passed its build, package signing, and 7/7 test_package assertions.
This diagnostic proves the prepared recipes integrate, but it does not make the
missing coordinates published and is not formal Shadow CI evidence. Details are
in `device-integration-prevalidation.md`.

## Decision

**W0 blocked.** R36 still requires GTK, libsndfile, and PortAudio to be merged
and published through their own issues/branches/PRs before formal abx Shadow CI
or submission. Their code is not copied into this branch. The branch must not
be marked `built`/`published` based on the diagnostic cache run.
