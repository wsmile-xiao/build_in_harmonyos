# Test report — SWH 0.4.17

## Current official finish validation

Run swh-w3-r11-20261012-official-finish-patch-dispatch passed the full native
recipe verification and official local CI (exit0), upstream 1/1 and consumers
6/6. All 12 receipts complete; release/postrelease PASS. Raw collected log
SHA256 d76a1f31c51c65b8761d5eb7ba1b37833c14ddfe1a35458915869e916ba60ef4.
Runtime candidate SHA256
d3d37fcedf3b95197a5385d5c4017b31f869a10db0ef04d45598ce7ed2a9b069.
Aggregate finish retained RC1 with only post-W3 step5b/step8 failures;
it is not reported as full finish PASS. Independent production submission
contracts handle those readiness checks. No worker CI or release claim.

## Earlier r9 validation

2026-10-12 native OHOS/armv8 Conan create RC0, run
swh-w3-r9-20261012-settings-in-build, one launch, all 12 receipts complete,
release/postrelease PASS. Complete log SHA256
e9b3f1e3eac39441d7c47f293b20507607ce0d4be145165513dcc5acdf487843.

Upstream: bozo 1/1, 100% (original checker, all 100 XML).
Consumers: 6/6, 100%: installed module inventory (96), descriptor identity
(109), amplifier unity, gain, additive processing, FFT equalizer audio.
FFT instantiate begin/complete and real finite nonzero audio/latency passed;
the 30-second failure alarm remains unchanged.

Runtime candidate SHA256
937b760077a21d895bc8895a3d1c779d3fe4fd561edcfad037e8346c0d133141;
package swh/0.4.17#b13abe968a1bb9e8bd74a7614fdee7ca:fde2c358280770451d1bd285abcc26b126974d4e#b2732b26314393aafdad633ae62f1b61.
This is native device evidence, not worker CI or release.
