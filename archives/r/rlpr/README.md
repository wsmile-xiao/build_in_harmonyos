# rlpr

rlpr provides four line-printer protocol commands: `rlpr`, `rlpq`, `rlprm`, and `rlprd`.
The 2.06 recipe builds upstream source and packages these commands without enabling
the upstream setuid or `/usr/bin` compatibility-link installation targets.

The 2.06 recipe passed a HarmonyOS PC `conan create` and four packaged-command
version checks on 2026-10-06. No live printer job, proxy or setuid installation
was exercised; platform PR CI remains pending.
