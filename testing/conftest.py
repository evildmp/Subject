from pathlib import Path
import sys
import time
import types

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeMicrobitEnv:
    def __init__(self):
        self.now_ms = 0
        self.sound = 0
        self.motion = 1070
        self.light = 0
        self.temp = 20
        self.pixels = [[0] * 5 for _ in range(5)]

    def make_module(self):
        env = self
        mod = types.ModuleType("microbit")
        mod.microphone = types.SimpleNamespace(sound_level=lambda: env.sound)
        mod.accelerometer = types.SimpleNamespace(get_strength=lambda: env.motion)
        mod.display = types.SimpleNamespace(
            read_light_level=lambda: env.light,
            set_pixel=lambda col, row, val: env.pixels[row].__setitem__(col, val),
        )
        mod.temperature = lambda: env.temp
        return mod


@pytest.fixture
def env(monkeypatch):
    fake = FakeMicrobitEnv()
    monkeypatch.setitem(sys.modules, "microbit", fake.make_module())
    monkeypatch.setattr(time, "ticks_ms", lambda: fake.now_ms, raising=False)
    monkeypatch.setattr(time, "ticks_diff", lambda new, old: new - old, raising=False)
    sys.modules.pop("subject", None)
    return fake
