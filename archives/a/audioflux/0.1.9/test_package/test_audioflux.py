#!/usr/bin/env python3
"""Conan test_package — audioflux 0.1.9 消费者用例。

通过已安装产物（PYTHONPATH 指向 site-packages + LD_LIBRARY_PATH 指向 lib/）
仅使用公开 API：import audioflux，构造 MelSpectrogram（公开类，公开枚举
类型），对 numpy 浮点信号调用 spectrogram() 并断言输出形状与有限值；
再经 ctypes 直接加载 libaudioflux.so 验证 C 层公开库可加载（公开产物）。
"""
import os
import sys
import ctypes
import numpy as np

import audioflux as af
import audioflux.type as aft


def main():
    checks = []

    # 公开 API 1: MelSpectrogram 谱图计算（上游 benchmark/run_audioflux.py 同款公开用法）
    mel = af.MelSpectrogram(num=128, samplate=32000, low_fre=0, high_fre=16000,
                            radix2_exp=11, slide_length=512,
                            window_type=aft.WindowType.HANN,
                            data_type=aft.SpectralDataType.POWER,
                            style_type=aft.SpectralFilterBankStyleType.SLANEY,
                            normal_type=aft.SpectralFilterBankNormalType.NONE)
    t = np.random.rand(4096).astype(np.float32) * 2.0 - 1.0
    spec = mel.spectrogram(t)
    assert spec is not None and spec.size > 0, "spectrogram 输出为空"
    assert np.isfinite(spec).all(), "spectrogram 输出含非有限值"
    checks.append(f"MelSpectrogram.spectrogram -> shape={spec.shape}, finite={np.isfinite(spec).all()}")

    # 公开 API 2: 版本号字段
    ver = getattr(af, "__version__", None)
    checks.append(f"audioflux.__version__ = {ver}")

    # 公开产物: ctypes 直接加载 libaudioflux.so（fftlib 同款加载路径）
    here = os.path.dirname(os.path.realpath(__file__))
    pkg_lib = os.path.join(here, "lib", "libaudioflux.so")
    lib = ctypes.cdll.LoadLibrary(pkg_lib) if os.path.exists(pkg_lib) else None
    if lib is not None:
        checks.append(f"ctypes loaded {pkg_lib}")
    else:
        import audioflux.fftlib as fl
        fp = fl.get_fft_lib_fp()
        ctypes.cdll.LoadLibrary(fp)
        checks.append(f"ctypes loaded {fp} (via fftlib)")

    for c in checks:
        print("CHECK:", c)
    print(f"PASS: {len(checks)} consumer checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())