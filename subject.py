from collections import namedtuple
import math
import microbit
import time


MOTION_CUTOFF = 4.0  # Hz
LIGHT_CUTOFF = 4.0  # Hz
AUDIO_CUTOFF = 10.0  # Hz
MOTION_BASELINE = 1070.0
MOTION_DEVIATION_MAX = 2394.0
SOUND_METER_MAX = 128.0
PULSE_FLASH_MS = 100


def draw_bar(col, value, max_value):
    """Light up display column `col` bottom-up in proportion to value / max_value."""
    level = min(max(value, 0) / max_value, 1) * 5
    for row in range(5):
        microbit.display.set_pixel(col, row, max(0, min(9, int((level - (4 - row)) * 9))))


Impression = namedtuple("Impression", ("mode", "t", "magnitude"))
Pulse = namedtuple("Pulse", ("mode", "start_t", "peak_t", "end_t", "peak"))


class LowPassFilter:
    """Single-pole low-pass filter adjusted for elapsed milliseconds."""

    def __init__(self, get_time, cutoff):
        self.get_time = get_time
        self.decay_rate = 2 * math.pi * cutoff / 1000.0
        self.y = None
        self.last_elapsed = None

    def update(self, x):
        elapsed_time = self.get_time()
        if self.y is None:
            self.y = x
        else:
            dt = max(0, elapsed_time - self.last_elapsed)
            alpha = 1 - math.exp(-self.decay_rate * dt)
            self.y += alpha * (x - self.y)
        self.last_elapsed = elapsed_time
        return self.y


class Manifold:
    """Instantaneous sensory manifold holding the current Impression for each mode."""

    def __init__(self):
        self.impressions = {}

    def add(self, impression):
        self.impressions[impression.mode] = impression


class Sensibility:
    """Receptive capacity of a Subject; time is the form of sensibility, so t lives here."""

    def __init__(self, subject):
        self.subject = subject
        self.manifold = Manifold()
        self.start = None
        get_time = lambda: self.t
        self.filters = {
            "sound": LowPassFilter(get_time, AUDIO_CUTOFF),
            "motion": LowPassFilter(get_time, MOTION_CUTOFF),
            "light": LowPassFilter(get_time, LIGHT_CUTOFF),
        }

    @property
    def t(self):
        """Elapsed milliseconds since the first read of t; begins at 0 on first access."""
        if self.start is None:
            self.start = time.ticks_ms()
            return 0
        return time.ticks_diff(time.ticks_ms(), self.start)

    def receive(self, mode, magnitude):
        if mode in self.filters:
            magnitude = self.filters[mode].update(magnitude)
        self.manifold.add(Impression(mode, self.t, magnitude))


class PulseSynthesiser:
    """Segments a single sensory stream into discrete rise-and-fall pulses."""

    def __init__(self, time_constant=1000.0, k=0.7, floor=1.0):
        self.decay_rate = 1.0 / time_constant
        self.k = k
        self.floor = floor
        self.mean = None
        self.deviation = 0.0
        self.last_t = None
        self.in_pulse = False
        self.start_t = None
        self.peak_t = None
        self.peak = None

    def unify(self, impression):
        t, x = impression.t, impression.magnitude
        if self.mean is None:
            self.mean = x
            self.last_t = t
            return None

        dt = max(0, t - self.last_t)
        alpha = 1 - math.exp(-self.decay_rate * dt)
        self.last_t = t

        delta = x - self.mean
        self.mean += alpha * delta
        self.deviation += alpha * (abs(delta) - self.deviation)

        threshold = max(self.floor, self.k * self.deviation)
        if not self.in_pulse:
            if x - self.mean > threshold:
                self.in_pulse = True
                self.start_t = t
                self.peak_t = t
                self.peak = x
            return None

        if x > self.peak:
            self.peak = x
            self.peak_t = t
        if x - self.mean < 0.5 * threshold:
            self.in_pulse = False
            return Pulse(impression.mode, self.start_t, self.peak_t, t, self.peak)
        return None


class Imagination:
    """Synthesises successive sensory impressions into coherent perceptual wholes."""

    def __init__(self, subject):
        self.subject = subject
        self.pulse_synthesisers = {
            "sound": PulseSynthesiser(),
            "motion": PulseSynthesiser(floor=15.0),
            "light": PulseSynthesiser(),
        }
        self.pulses = []

    def synthesise(self):
        impressions = self.subject.sensibility.manifold.impressions
        self.pulses = []
        for mode, synthesiser in self.pulse_synthesisers.items():
            if mode in impressions:
                pulse = synthesiser.unify(impressions[mode])
                if pulse is not None:
                    self.pulses.append(pulse)


class Expression:
    """Renders the subject's sensory impressions and synthesised pulses onto the display."""

    def __init__(self, subject):
        self.subject = subject
        self.flash_until = {"motion": 0, "sound": 0}

    def draw(self):
        now = self.subject.sensibility.t
        impressions = self.subject.sensibility.manifold.impressions

        for pulse in self.subject.imagination.pulses:
            if pulse.mode in self.flash_until:
                self.flash_until[pulse.mode] = now + PULSE_FLASH_MS

        if "motion" in impressions:
            draw_bar(0, abs(impressions["motion"].magnitude - MOTION_BASELINE), MOTION_DEVIATION_MAX)
        if "sound" in impressions:
            draw_bar(3, impressions["sound"].magnitude, SOUND_METER_MAX)

        motion_brightness = 9 if now < self.flash_until["motion"] else 0
        sound_brightness = 9 if now < self.flash_until["sound"] else 0
        for row in range(5):
            microbit.display.set_pixel(1, row, motion_brightness)
            microbit.display.set_pixel(4, row, sound_brightness)


class Subject:
    """Cognitive subject whose powers operate within a single running time."""

    def __init__(self):
        self.sensibility = Sensibility(self)
        self.imagination = Imagination(self)
        self.expression = Expression(self)
        self.running = self.run()

    def run(self):
        """Running-time generator; steps the subject's powers once per next() call."""
        while True:
            self.imagination.synthesise()
            self.expression.draw()

            yield


def affect(sensibility):
    """Read hardware outside the cognitive model and deliver values to Sensibility."""
    sensibility.receive("sound", microbit.microphone.sound_level())
    sensibility.receive("light", microbit.display.read_light_level())
    sensibility.receive("motion", microbit.accelerometer.get_strength())


if __name__ == "__main__":
    subject = Subject()
    while True:
        affect(subject.sensibility)
        next(subject.running)
