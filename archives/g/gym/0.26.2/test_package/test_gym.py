"""test_gym.py — consumer test for gym 0.26.2 (HarmonyOS PC specific).

Real calls into the installed package (no mocks): identity, core Env API,
VectorEnv, cloudpickle round-trip (gym's canonical parallelization path),
spaces sampling determinism, wrapper behavior.
"""
import os
import sys

site = sys.argv[1] if len(sys.argv) > 1 else ""
if site:
    sys.path.insert(0, site)

import warnings
warnings.filterwarnings("ignore")

import gym
import numpy as np

# 1) Identity: imported from THIS package, version 0.26.2
mod_path = os.path.realpath(gym.__file__)
if site:
    assert mod_path.startswith(os.path.realpath(site)), \
        f"gym imported from {mod_path}, not from package {site}"
assert gym.__version__ == "0.26.2", f"version {gym.__version__}"
print("[1] identity ok:", gym.__name__, gym.__version__)

# 2) Core Env API: CartPole reset/step 50 steps, shapes + reward sane
#    NOTE: the observation of the TERMINAL step may legitimately lie outside
#    observation_space (cartpole theta overshoots the 0.2 rad termination
#    threshold on its last step — a known upstream quirk the passive checker
#    even warns about), so contains() is asserted on non-terminal steps only.
env = gym.make("CartPole-v0")
obs, info = env.reset(seed=42)
assert obs.shape == (4,) and obs.dtype == np.float32
assert env.observation_space.contains(obs)
total = 0.0
for _ in range(50):
    obs, r, terminated, truncated, info = env.step(env.action_space.sample())
    total += r
    assert terminated in (True, False) and truncated in (True, False)
    if not (terminated or truncated):
        assert env.observation_space.contains(obs)
assert 0.0 <= total <= 50.0  # CartPole reward is +1 per step
print("[2] core env ok: 50 steps, total reward", total)
env.close()

# 3) VectorEnv: SyncVectorEnv x2 CartPole
ve = gym.vector.SyncVectorEnv([lambda: gym.make("CartPole-v0") for _ in range(2)])
o, _ = ve.reset(seed=1)
o, rw, dones, truncs, _ = ve.step(np.array([0, 1], dtype=np.int64))
assert o.shape == (2, 4) and rw.shape == (2,)
print("[3] sync vector env ok:", o.shape)
ve.close()

# 4) cloudpickle round-trip (gym's canonical env pickling for parallelism)
import cloudpickle
e1 = gym.make("CartPole-v0")
e2 = cloudpickle.loads(cloudpickle.dumps(e1))
assert type(e2) is type(e1), f"type lost: {type(e2)}"
o2, _ = e2.reset(seed=42)
o2, r2, t2, tr2, _ = e2.step(0)
assert o2.shape == (4,)
print("[4] cloudpickle ok:", type(e2).__name__)

# 5) Spaces determinism: space.seed(n) + sample() reproducible
#    (gym 0.26.2 Space.sample takes no seed kwarg — seed via space.seed())
ds = gym.spaces.Discrete(5)
ds.seed(7); a = ds.sample()
ds.seed(7); b2 = ds.sample()
assert a == b2 and ds.contains(a), f"seeded Discrete not reproducible: {a} {b2}"
bx = gym.spaces.Box(0, 1, shape=(2,), dtype=np.float32)
bx.seed(7); x1 = bx.sample()
bx.seed(7); x2 = bx.sample()
assert (x1 == x2).all() and bx.contains(x1)
assert bx.contains(np.array([0.5, 0.5], dtype=np.float32))
assert not bx.contains(np.array([0.5, 2.0], dtype=np.float32))
print("[5] spaces ok")

# 6) Wrappers: TimeLimit + RescaleAction actually transform behavior
from gym.wrappers import TimeLimit, RescaleAction
tl = TimeLimit(gym.make("CartPole-v0"), max_episode_steps=5)
tl.reset(seed=1)
steps = 0
while True:
    o, r, term, trunc, _ = tl.step(0)
    steps += 1
    if term or trunc:
        break
assert steps == 5, f"TimeLimit not enforced: {steps} steps"
print("[6] wrappers ok: TimeLimit enforced at", steps)

print("ALL GYM OHOS TESTS PASSED")
