# Draft 12001 — runenv_info is last-writer-wins: a package re-declaring a dependency's env var ships a broken path

Discovered while adapting **tmatrix 1.4** to HarmonyOS PC (OHOS aarch64) against the published **ncurses/6.6** package.

## What happened

The first version of `archives/t/tmatrix/1.4/conanfile.py` ended `package_info()` like this:

```python
self.runenv_info.define_path("TERMINFO", os.path.join(self.package_folder, "share", "terminfo"))
self.runenv_info.define_path("TERMINFO_DIRS", os.path.join(self.package_folder, "share", "terminfo"))
```

It looked correct — tmatrix is a terminal application, and ncurses needs a terminfo database. But tmatrix's build never creates `share/terminfo`; the database ships **inside the ncurses package**. Conan's `runenv_info` is merged across the graph and the last definition of a variable wins, so these two lines *shadowed* the correct values coming from `ncurses/6.6`.

Measured on a consumer that requires only the application:

```
$ conan install --requires=tmatrix/1.4 -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl
$ cat conanrunenv-release-armv8.sh
export TERMINFO=".../tmatrix-....../p/share/terminfo"     # <- directory never created
```

`conan create` passed, every build gate passed, and nothing warned. Only a consumer-side check exposed it.

## Why "just point it at the ncurses package" is also wrong

The obvious repair is to derive the path from the dependency instead of from `self`. Both variants fail during a **consumer** graph resolution:

| Attempt | Result |
|---|---|
| `ncurses.package_folder` | `TypeError: expected str, bytes or os.PathLike object, not NoneType` — it is `None` |
| `os.path.dirname(ncurses.cpp_info.includedirs[0])` | `includedirs == ['include']` (relative), so the root comes out as `.` and the path as `share/terminfo` |

Instrumenting a throwaway copy of the recipe shows it plainly:

```
tmatrix/1.4: DBG2 nc=ncurses/6.6 pkg_folder=None
```

The dependency's folders are only absolute while that dependency is being **built in the same run**. From the cache, they are relative.

## The rule that holds

**Own your runenv.** A package must only export environment variables for files it actually packages. A variable owned by a dependency is that dependency's to export, and consumers inherit it by requiring that package directly:

```
# consumer that also requires ncurses -> correct, resolvable path
$ conan install --requires=tmatrix/1.4 --requires=ncurses/6.6 ...
export TERMINFO=".../ncurs780a5e6acf3cf/p/share/terminfo"   # contains x/xterm
```

`test_package/` therefore lists `ncurses/6.6` as a direct requirement, which is both how it gets the runenv and what makes the test meaningful.

## Check to run on any application package

Do this from the **consumer** side, never from the build side:

```bash
mkdir -p /tmp/probe && cd /tmp/probe
conan install --requires=<pkg>/<ver> -pr:h=<profile> -pr:b=<profile>
cat conanrunenv-*.sh          # every exported path must exist
```

## Related, but a separate trap

The published `ncurses/6.6` is configured without `USE_ROOT_ENVIRON`, so
`use_terminfo_vars()` resolves to `_nc_env_access()`, which returns **false when
`euid == 0`**. A root-run test therefore cannot reach a terminfo database at all,
no matter what `TERMINFO` says:

```
$ TERMINFO=<ncurses>/share/terminfo tmatrix --version   # as root
ncurses: cannot initialize terminal type ($TERM="xterm"); exiting
$ ...                                                    # as an unprivileged uid
<frame painted>
```

That is a property of the dependency, not of the recipe, and it is why
`test_tmatrix.sh` asserts that the render path was *entered* (escape sequence,
ncurses diagnostic, or still running at the timeout) and treats the frame-content
check as a conditional skip rather than reporting it as a pass.
