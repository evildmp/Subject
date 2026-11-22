from collections import namedtuple
import math
import microbit
import time


# sensory constants; cutoff values represent the frequency above which signals are attenuated

MOTION_CUTOFF = 4.0  # Hz
LIGHT_CUTOFF = 4.0  # Hz
AUDIO_CUTOFF = 10.0  # Hz
GRAVITATIONAL_ACCELERATION = 1070.0  # gravity is always present

# subject's internal state

PLEASURE_CONFIDENCE = 5  # threshold: confidence instances required for pleasure

# maximimum sensor values for expression calibration

MOTION_DEVIATION_MAX = 2394.0  # not actually a raw sensor value; takes gravity into account
SOUND_METER_MAX = 128.0
LIGHT_METER_MAX = 255.0
SENSOR_BRIGHTNESS = 5

# expression display settings
CONFIDENCE_BRIGHTNESS = 9
PLEASURE_FLASH_MS = 80

# the forms of sensory impression and discrete representations in the imagination

Impression = namedtuple("Impression", ("mode", "t", "magnitude"))
Pulse = namedtuple("Pulse", ("mode", "start_t", "peak_t", "peak"))


class Subject:

    def __init__(self):
        #  the faculties

        self.sensibility = Sensibility(self)
        self.imagination = Imagination(self)
        self.understanding = Understanding(self)

        self.expression = Expression(self)  # not a faculty
        self.active = self.attend()

    def attend(self):
        """Running-time generator; steps the subject's powers once per next() call."""
        while True:
            self.imagination.synthesise()
            self.understanding.judge()
            self.understanding.anticipate()
            self.expression.draw()

            yield


class Sensibility:
    """Receptive capacity of a Subject; time is the form of sensibility, so t lives here."""

    def __init__(self, subject):
        self.subject = subject
        self.manifold = Manifold()  # impressions are received in the manifold

        # The filters represent smoothing of sensory signals, at the organic level.
        self.filters = {
            "sound": LowPassFilter(AUDIO_CUTOFF),
            "motion": LowPassFilter(MOTION_CUTOFF),
            "light": LowPassFilter(LIGHT_CUTOFF),
        }

    @property
    def t(self):
        """Current time in milliseconds; time is the form of sensibility."""
        return time.ticks_ms()

    def receive(self, mode, magnitude):
        t = self.t
        if mode in self.filters:
            magnitude = self.filters[mode].update(magnitude, t)
        self.manifold.add(Impression(mode, t, magnitude))


class Manifold:
    """Instantaneous sensory manifold holding the current Impression for each mode."""

    def __init__(self):
        # Wwhen populated the impressions dictionary will contain a key for each sense,
        # and a corresponding Impression namedtuple as its value.
        self.impressions = {}

    def add(self, impression):
        self.impressions[impression.mode] = impression


class LowPassFilter:
    """Single-pole low-pass filter adjusted for elapsed milliseconds."""

    def __init__(self, cutoff):
        self.decay_rate = 2 * math.pi * cutoff / 1000.0
        self.y = None
        self.last_t = None

    def update(self, x, t):
        if self.y is None:
            self.y = x
        else:
            dt = max(0, t - self.last_t)
            alpha = 1 - math.exp(-self.decay_rate * dt)
            self.y += alpha * (x - self.y)
        self.last_t = t
        return self.y


class Imagination:
    """Synthesises successive sensory impressions into coherent perceptual wholes."""

    def __init__(self, subject):
        self.subject = subject

        # At present, we only admit of one kind of event: Pulses. There could be others in
        # the future, but for now, we'll keep it simple. For each sensory mode there is a
        # PulseSynthesiser, that is able to apprehend discrete events in the stream of
        # impressions.

        self.pulse_synthesisers = {
            "sound": PulseSynthesiser(time_constant=2000.0, k=2.3, floor=10.0),
            "motion": PulseSynthesiser(floor=15.0, min_impulse=2000.0),
            "light": PulseSynthesiser(),
        }
        self.pulses = []

    def synthesise(self):
        now = self.subject.sensibility.t
        impressions = self.subject.sensibility.manifold.impressions
        schemas = self.subject.understanding.schemas
        self.pulses = []
        for mode, synthesiser in self.pulse_synthesisers.items():
            schema = schemas.get(mode)
            pulse = None
            if mode in impressions:
                pulse = synthesiser.apprehend(impressions[mode], schema=schema)
            if pulse is None and schema is not None and not synthesiser.in_pulse:
                if schema.can_cover_miss and schema.is_overdue(now):
                    pulse = Pulse(mode, schema.expected_t, schema.expected_t, 0)
            if pulse is not None:
                self.pulses.append(pulse)


class PulseSynthesiser:
    """Segments a single sensory stream into discrete rise-and-fall pulses."""

    def __init__(self, time_constant=1000.0, k=0.7, floor=1.0, min_impulse=0.0):
        self.decay_rate = 1.0 / time_constant
        self.k = k
        self.floor = floor
        self.min_impulse = min_impulse
        self.mean = None
        self.deviation = 0.0
        self.last_t = None
        self.in_pulse = False
        self.emitted = False
        self.start_t = None
        self.peak_t = None
        self.peak = None
        self.impulse = 0.0

    def apprehend(self, impression, schema=None):
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

        gain = schema.gain() if (schema is not None and schema.agrees(t)) else 0.0
        eff_floor = self.floor * (1.0 - 0.4 * gain)
        eff_min_impulse = self.min_impulse * (1.0 - 0.4 * gain)

        threshold = max(eff_floor, self.k * self.deviation)
        if not self.in_pulse:
            if x - self.mean > threshold:
                self.in_pulse = True
                self.emitted = False
                self.start_t = t
                self.peak_t = t
                self.peak = x
                self.impulse = 0.0
            return None

        self.impulse += max(0.0, x - self.mean) * dt
        pulse = None
        if not self.emitted:
            if x > self.peak:
                self.peak = x
                self.peak_t = t
            elif (self.peak - x >= 0.25 * threshold or x - self.mean < 0.5 * threshold) and self.impulse >= eff_min_impulse:
                self.emitted = True
                peak_t = schema.pull_time(self.peak_t) if schema is not None else self.peak_t
                pulse = Pulse(impression.mode, self.start_t, peak_t, self.peak)

        if x - self.mean < 0.5 * threshold:
            self.in_pulse = False
            self.emitted = False
        return pulse


class Understanding:
    """Applies provisional temporal rules to the pulses synthesised by Imagination."""

    def __init__(self, subject):
        self.subject = subject

        # a rule recognises a certain kind of formal pattern
        self.rules = {
            "sound": EqualityOfInterval("sound"),
            "motion": EqualityOfInterval("motion"),
            "light": EqualityOfInterval("light"),
        }
        self.schemas = {}
        self.anticipated = {}
        self.last_anticipated_t = {}

    def judge(self):
        now = self.subject.sensibility.t
        pulses_by_mode = {p.mode: p for p in self.subject.imagination.pulses}
        self.schemas = {}
        for mode, rule in self.rules.items():
            in_pulse = self.subject.imagination.pulse_synthesisers[mode].in_pulse
            schema = rule.apply_rule(pulses_by_mode.get(mode), now, in_pulse=in_pulse)
            if schema is not None:
                self.schemas[mode] = schema

    def anticipate(self):
        now = self.subject.sensibility.t
        self.anticipated = {}
        for mode, schema in self.schemas.items():
            if schema.is_due(now) and self.last_anticipated_t.get(mode) != schema.expected_t:
                self.last_anticipated_t[mode] = schema.expected_t
                self.anticipated[mode] = schema


class EqualityOfInterval:
    """Tracks a provisional temporal interval rule for a single sensory mode. This is currently the only rule we have, but any future rules will share the same shape.
    """

    def __init__(self, mode, tolerance=0.2, min_interval=150, max_interval=2000):
        self.mode = mode
        self.tolerance = tolerance
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.last_t = None
        self.interval = None
        self.expected_t = None
        self.confidence = 0
        self.beats_since_miss = 4

    def schema(self):
        if self.expected_t is None:
            return None
        can_cover = self.confidence >= PLEASURE_CONFIDENCE and self.beats_since_miss >= 4
        return Schema(self.mode, self.interval, self.expected_t, self.confidence, self.tolerance, can_cover)

    def apply_rule(self, pulse, now, in_pulse=False):
        if pulse is not None:
            t = pulse.peak_t
            if self.last_t is None:
                self.last_t = t
                return None

            dt = t - self.last_t
            if dt <= 0:
                return self.schema()

            if self.expected_t is not None and abs(t - self.expected_t) <= self.tolerance * self.interval:
                if pulse.peak == 0:
                    self.beats_since_miss = 0
                else:
                    self.interval = 0.5 * self.interval + 0.5 * dt
                    self.confidence += 1
                    self.beats_since_miss += 1
                self.last_t = t
                self.expected_t = t + self.interval
                return self.schema()

            self.last_t = t
            self.beats_since_miss = 4
            if self.min_interval <= dt <= self.max_interval:
                self.interval = dt
                self.confidence = 0
                self.expected_t = t + dt
            else:
                self.interval = None
                self.expected_t = None
                self.confidence = 0
            return self.schema()

        if not in_pulse and self.expected_t is not None and now > self.expected_t + self.tolerance * self.interval:
            self.interval = None
            self.expected_t = None
            self.confidence = 0
            self.beats_since_miss = 4
        return self.schema()


class Schema:
    """Temporal mediation between Understanding's rule and Imagination."""

    def __init__(self, mode, interval, expected_t, confidence=0, tolerance=0.2, can_cover_miss=False):
        self.mode = mode
        self.interval = interval
        self.expected_t = expected_t
        self.confidence = confidence
        self.tolerance = tolerance
        self.can_cover_miss = can_cover_miss

    def agrees(self, t):
        return self.confidence >= 1 and abs(t - self.expected_t) <= self.tolerance * self.interval

    def gain(self):
        return min(self.confidence, 5) / 5.0

    def pull_time(self, peak_t):
        if not self.agrees(peak_t):
            return peak_t
        pull = 0.2 * self.gain()
        return int(round(peak_t + pull * (self.expected_t - peak_t)))

    def is_due(self, now):
        return self.confidence >= 1 and now >= self.expected_t

    def is_overdue(self, now):
        return now > self.expected_t + self.tolerance * self.interval


class Expression:
    """Communicates the internal states and jdugements of the Subject. That includes
    via the built-in display, and over radio to any micro:bits that might be
    listening.
    """

    COLUMNS = (("motion", 0), ("sound", 2), ("light", 4))

    def __init__(self, subject):
        self.subject = subject
        # we need to keep a record of the timestamp when pleasure related to a mode
        self.pleasure_start = {"motion": None, "sound": None, "light": None}
        # a record of the last time it was expressed, to help avoid repeating it
        self.last_expressed_t = {"motion": None, "sound": None, "light": None}

    def draw(self):
        now = self.subject.sensibility.t
        impressions = self.subject.sensibility.manifold.impressions
        schemas = self.subject.understanding.schemas

        for mode, col in self.COLUMNS:
            schema = schemas.get(mode)
            confidence = schema.confidence if schema is not None else 0

            if confidence >= PLEASURE_CONFIDENCE:
                if now >= schema.expected_t and schema.expected_t != self.last_expressed_t[mode]:
                    self.pleasure_start[mode] = now
                    self.last_expressed_t[mode] = schema.expected_t

                start = self.pleasure_start[mode]
                if start is not None:
                    if now - start < PLEASURE_FLASH_MS:
                        for row in range(5):
                            microbit.display.set_pixel(col, row, CONFIDENCE_BRIGHTNESS)
                        continue
                    self.pleasure_start[mode] = None
                for row in range(5):
                    microbit.display.set_pixel(col, row, 0)
                continue

            self.pleasure_start[mode] = None
            self.last_expressed_t[mode] = None

            if mode in impressions:
                magnitude = impressions[mode].magnitude
                if mode == "motion":
                    draw_sensor_bar(col, abs(magnitude - GRAVITATIONAL_ACCELERATION), MOTION_DEVIATION_MAX)
                elif mode == "sound":
                    draw_sensor_bar(col, magnitude, SOUND_METER_MAX)
                else:
                    draw_sensor_bar(col, magnitude, LIGHT_METER_MAX)
            else:
                for row in range(5):
                    microbit.display.set_pixel(col, row, 0)

            for i in range(min(confidence, 5)):
                microbit.display.set_pixel(col, 4 - i, CONFIDENCE_BRIGHTNESS)


def draw_sensor_bar(col, value, max_value):
    """Light up display column `col` top-down at ~55% brightness."""
    level = min(max(value, 0) / max_value, 1) * 5
    for row in range(5):
        microbit.display.set_pixel(col, row, max(0, min(SENSOR_BRIGHTNESS, int((level - row) * SENSOR_BRIGHTNESS))))


def affect(sensibility):
    """Read hardware outside the cognitive model and deliver values to Sensibility."""
    sensibility.receive("sound", microbit.microphone.sound_level())
    sensibility.receive("light", microbit.display.read_light_level())
    sensibility.receive("motion", microbit.accelerometer.get_strength())


# the entry-point into this world

if __name__ == "__main__":
    # creates the subject with its powers, and the generator in Subject.attend()
    subject = Subject()

    # the "world loop"
    while True:
        # the world's objects affect the subject's sensibility
        affect(subject.sensibility)
        # advances to the next cycle of the generator
        next(subject.active)
