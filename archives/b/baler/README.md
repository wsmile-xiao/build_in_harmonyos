# baler

Baler is a machine learning based data compression tool that uses autoencoders to compress and decompress multi-dimensional scientific data. It provides train, compress, decompress and plotting workflows plus energy and PyTorch profiling.

This directory contains the OpenHarmony PC Conan recipe for baler.

## OHOS adaptation
- **Build system**: Python (poetry) pure-python package, no native compilation. Adapted as Conan application package by copying pure-python sources.
- **Python version**: Upstream requires Python >=3.8,<3.11; patched to allow Python 3.12 on OHOS (see 0001 patch).
- **Dependencies**: Runtime pip dependencies (torch, numpy 1.23.5, scikit-learn, matplotlib, tqdm, codecarbon) are optional at Conan package time; heavy ML wheels (torch) not vendored for OHOS aarch64, documented as runtime pip install.
- **Entry point**: Installs wrapper script `bin/baler` that invokes `baler.baler:main`.

## Dependencies
- python/3.12.9 (tool)
- pip-based: torch >=2.0.0, numpy 1.23.5, scikit-learn, matplotlib, tqdm, codecarbon (optional: hls4ml, tensorflow)

## References
- https://github.com/baler-collaboration/baler
- https://zenodo.org/records/10723669 (1.4.0 release)
