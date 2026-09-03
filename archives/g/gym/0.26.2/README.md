# gym 0.26.2 (HarmonyOS PC)

Reinforcement learning environment toolkit — [openai/gym](https://github.com/openai/gym) 0.26.2,
the last official openai release (MIT). Pure Python, zero source modifications for OHOS aarch64.

## Usage

```python
import gym
import numpy as np

env = gym.make("CartPole-v0")
obs, _ = env.reset(seed=42)
obs, reward, terminated, truncated, _ = env.step(env.action_space.sample())
```

## Package layout

- `lib/python3.12/site-packages/gym/` — the `gym` package
- `licenses/` — MIT license

## Runtime dependencies (private dir, pip --target)

`numpy==1.26.4`, `cloudpickle==3.1.2`, `gym_notices==0.1.0` (plus pytest
for the build-time test run) are installed by the recipe into a private
directory (`build_folder/pydeps`) from the internal mirror. `PYTHONNOUSERSITE=1`
is forced because the worker baseline python's user-site holds a numpy 2.x
whose .so is not readable by the worker uid (dlopen EACCES) and is
unsupported by gym 0.26.2 anyway.

## Testing

- Upstream pytest full suite (1336 tests) runs FOR REAL in `build()` on OHOS
  aarch64, unmodified: baseline 1242 passed / 81 failed / 13 skipped
  (all 81 environmental — numpy np.bool8 deprecation assertions, missing
  optional box2d/moviepy/ale extras, Py3.12 changes — 0 OHOS regressions).
  4 collection-broken files (optional extras) declared in
  `test_package/MANIFEST.yml` per TEST_QUALITY_SPEC 3.3.
- `test_package/test_gym.py` — 6 HarmonyOS-PC-specific consumer checks.

See `notes.md` for adaptation details.
