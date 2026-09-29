# zshdb/1.1.4 for HarmonyOS PC

zshdb is a debugger for zsh scripts. This Conan recipe packages the official
1.1.4 release for HarmonyOS PC AArch64. The target has zsh 5.9, but its
minimal installation lacks `is-at-least`, `zsh/mapfile` and optional PCRE
captures. The recipe ships the official zsh function with its license and
provides feature fallbacks, writable temporary storage, and relocatable
package-data paths.

The release tarball omits three assets for an integration test; the recipe
restores them byte-for-byte from the upstream 1.1.4 Git tag. Its native
`conan create` executes 5 Automake unit cases, 34 shunit functions with
216 assertions, all 27 integration cases, and a separate installed-package
consumer that debugs a real script. Interactive and editor integration are
outside the verified scope. Details and hashes are in `1.1.4/notes.md`.
