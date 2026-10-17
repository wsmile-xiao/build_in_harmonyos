# cubicsdr

CubicSDR — cross-platform Software Defined Radio application (wxWidgets GUI + liquid-dsp DSP + SoapySDR hardware abstraction).

On HarmonyOS PC this package delivers the DSP core library (`libcubicsdr-core.a`): the modem engine with 23 demodulation modes (10 analog + 13 digital), the IO thread framework, and the DataTree serialization backend — compiled verbatim from upstream sources. See `0.2.7/notes.md` for the full scope declaration (GUI front-end, demod orchestration and SDR device threads are out of the core cut; no wxCore GUI / desktop GL on the platform).

## 版本
- 0.2.7（上游 tag ba7a35c，2026-09-20 适配）
