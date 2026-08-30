# W0 dependency report

## Target

- Upstream project: GTK+ 3.24.38
- Conan package: `gtk/3.24.38`
- Issue: AtomGit #32
- Checked: 2026-08-17
- Remote: `ohpcd`
- Conan: 2.29.1 on HarmonyOS aarch64
- Isolation: per-run `CONAN_HOME` under the device test runner
- Dependency runner: `/storage/Users/currentUser/ohos-test-runs/codex-gtkplus-issue-32-w0-20260817-120153-49911`
- Coordinate runner: `/storage/Users/currentUser/ohos-test-runs/codex-gtk-issue-32-w0-coordinate-20260817-122632-61148`

## Direct recipe availability

| Reference | Recipe revision | Result |
|---|---|---|
| `glib/2.84.0.1` | `75f29176eede55310742f73ebcf9a572` | present |
| `cairo/1.18.4` | `7b98eb9b1eee6315f8a42c74c7af44d3` | present |
| `cairo-gobject/1.18.4` | `d0d32ef173885596c4164bc790f0fdf0` | present |
| `fontconfig/2.18.1.1` | `a6188062251a58f38b8428df3ed889fc` | present |
| `pango/1.56.4` | `3d4a1b71de75db88502bbbb086e4bb05` | present |
| `harfbuzz/14.2.0` | `0df732a07390f7983ed163093dad69e3` | recipe and OHOS/shared binary present |
| `gdk-pixbuf/2.44.6` | `dd84a01ac263b78875a2b828a950ac1a` | present |
| `atk/2.38.0.1` | `a5928c1951e0fea50e7acc5bbf687a3b` | present |
| `fribidi/1.0.16` | `5487479b1500a5d06a3f4637f79844e4` | present |
| `libepoxy/1.5.10` | `92f7e70c459ed2e6a96cd82549e82391` | present |
| `zlib/1.3.1.1` | `9a23e7d51311d0440b6e4d36cf44e4d9` | present |

Harfbuzz 14.2.0 provides OHOS/shared package ID
`02e364f2d646dda8acabc40d95696553e6e53235`. Harfbuzz 14.2.0.1 was not
selected because its only published binary references static GLib package ID
`7bf99b8d7dd456da94d1e65144dfaf646081e83d`, which is no longer present in
the remote; the only current GLib binary is shared package ID
`b55f7a483155972128ae18c9f9e8c67eba35e745`.

Pango 1.56.4 declares the exact `harfbuzz/14.2.0.1` reference. Because GTK also
uses HarfBuzz directly, the recipe uses `force=True` on `harfbuzz/14.2.0` to
retain the direct dependency while overriding that unusable transitive pin.

The target lookup for `gtk/3.24.38` returned the remote missing-reference
response (`system acceleration policy not enabled`, exit 1). This is the
remote's established absent-package response and confirms that the target
coordinate is unoccupied.

## Source and build-system checks

- Huawei Cloud GNOME mirror archive downloaded successfully
- Source SHA-256 matched `ce11decf018b25bdd8505544a4f87242854ec88be054d9ade5f3a20444dd8ee7`
- Official GNOME URL remains the fallback source
- Upstream Meson options confirm Broadway can be enabled while X11, Wayland,
  Win32, Quartz, tests, demos, examples, introspection, and documentation are
  independently disabled
- The Broadway Python-helper patch passed strict `git apply --check`

## Decision

R42 rejects `+` in a Conan package name, so the upstream name GTK+ is mapped
to the canonical package slug `gtk`. This matches the gate's documented
normalization rule and keeps the package name equal to its directory name.

W0 passes. The declared direct dependency recipe graph is available from
`ohpcd`, no missing dependency needs a separate adaptation issue, and work can
continue within the gtk 3.24.38 version directory.
