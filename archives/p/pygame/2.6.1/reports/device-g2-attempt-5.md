# HarmonyOS PC final verification

- Evidence archive: `pygame-device-results(5).tar.gz`
- Evidence archive SHA256:
  `fefe05fe105950512d39bfae50353dbbd43a3d6d0c8a90c9b0b9983057fe1283`
- Run ID: `20260905T181436Z-54433`
- Environment: HarmonyOS PC aarch64, CPython 3.12.9, OHOS Clang 15.0.4
- G2: pass
- W3: pass
- W3 integrity hash: `3eece1eee3fba97e`
- W3 log SHA256:
  `fb2439568a14381e58a79392dc95f3108ed83faed32bbf3083471241abd81c45`
- Session log SHA256:
  `059c3198ea7c2de2cec8936a68dd6453518171cb32ccab8aaf0c00325bd1973e`
- Runner exit code: 0

The recorded W3 log hash was independently recomputed from the compressed
evidence archive and matches `.ci-result.json`. W3 reported `KC_RESULT=pass`,
`JC_RESULT=pass`, L0/L1/L4/L5 pass, and the applicable L2 `no bin/` skip. Its
package summary was one success, zero failures, and a 100% pass rate.

The installed final wheel ran the exact 1,855-case, 44-module upstream
inventory. Results were 1,768 ordinary passes, 14 expected failures, 73
declared skips, zero failures, and zero errors. The declared skips are the 45
upstream/dummy-driver baseline cases plus 15 unavailable system-font provider
cases, 8 unavailable PortMidi cases, and 5 pure-OGG cases. Three mixed OGG/WAV
tests retained and executed their WAV branches. The SDL_ttf script-shaping
test validated the real unsupported-feature error path.

The original upstream `mixer_test.ChannelTypeTest.test_queue`, including its
immediate post-stop assertions, passed with the source patch. The packaged
consumer also passed 34/34 assertions, including immediate idle state and an
empty queue after `Channel.stop()`. Its structured result additionally reports
`sdlDynamicApiClean=true`, and the W3 log contains no SDL override diagnostic.

The pinned repository's finish command returned 1 because it counted four
pre-existing shared knowledge-graph fields and two v3-deprecated archive paths
as incomplete. The active archive specification explicitly deprecates
`packaging/` and `.staging-verified`, and SKILL v12.19 classifies W5,
finalize-archive, and submit-readiness findings as non-blocking. No deprecated
artifact or marker is added to this package. The delivery runner verified this
warning set exactly, along with the W3 integrity and structured test markers,
then continued to the standalone device consumer, negative control, and
artifact manifest. The overall runner returned 0.

The standalone minimal validation package installed the exact signed wheel and
passed 34/34 assertions with exit code 0. The negative control repeated the 34
functional passes, failed injected assertion 35, and returned 1. Neither log
contains the SDL override diagnostic. Artifact evidence is:

| File | Size | SHA256 |
|---|---:|---|
| `pygame-2.6.1-cp312-cp312-ohos_aarch64.whl` | 17,507,956 | `5fb4cdcfa7f56461b00a612c2c79086bd4066ca5efb459bff4314eb18c2c6246` |
| `test_pygame.py` | 9,818 | `636d53b3a46343284df1dc8b551a5fc09b26721007e187bd337981d449b3b419` |

The wheel ZIP contains 635 entries and passes a complete CRC check. The
artifact-manifest SHA256 is
`10f1050af6034d97d018d0af3cb249aba56a067cea57b3ba26246590ac0656d0`;
the normal and negative-control log SHA256 values are respectively
`4d2d09fe350747eb6158c43a9aaff78a0cd97d852cbd63e8718e950f9f60ce6b`
and `71c596fdfdb25b83b273e5bb56c9734f4c81556764d843c56317c20373cf6c6e`.

The selected device run used repository baseline
`f5131ee224ce0f5028e6bba671ea1a1f23342f35`. Before the final W4 audit, the
task branch was rebased to current `upstream/main` at
`dfe3d3ac77fa7afa801d0a7223122e63f43802c3`. The intervening range changes no
pygame or selected dependency recipe. Its target-profile delta restores only
the OHOS LLVM `libxml2` loader path, and its CI package-loop delta only extends
the root-file allowlist. The source patch, runner baseline, preflight, and W4
evidence are regenerated on the final base as required.
