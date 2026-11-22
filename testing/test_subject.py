import csv
from pathlib import Path
import statistics

DATASETS = Path(__file__).resolve().parent.parent / "datasets"


def replay_csv(env, filename, value_column, attr_name):
    import subject as subject_mod

    s = subject_mod.Subject()
    pulses = []
    with open(DATASETS / filename, newline="") as f:
        for row in csv.DictReader(f):
            env.now_ms = int(row["t_ms"])
            setattr(env, attr_name, float(row[value_column]))
            subject_mod.affect(s.sensibility)
            next(s.active)
            pulses.extend(s.imagination.pulses)
    return pulses


def test_subject_instantiation_and_sensibility_time(env):
    import subject as subject_mod

    s = subject_mod.Subject()
    env.now_ms = 500
    assert s.sensibility.t == 500
    env.now_ms = 525
    assert s.sensibility.t == 525


def test_sensibility_manifold_and_filtering(env):
    import subject as subject_mod

    s = subject_mod.Subject()
    env.now_ms = 0
    s.sensibility.receive("sound", 0.0)
    s.sensibility.receive("temperature", 21)

    env.now_ms = 20
    s.sensibility.receive("sound", 100.0)
    s.sensibility.receive("temperature", 25)

    sound_imp = s.sensibility.manifold.impressions["sound"]
    temp_imp = s.sensibility.manifold.impressions["temperature"]
    assert sound_imp.t == 20
    assert 0.0 < sound_imp.magnitude < 100.0
    assert temp_imp.magnitude == 25


def test_pulse_synthesiser_quiet_produces_no_pulses(env):
    import subject as subject_mod

    synth = subject_mod.PulseSynthesiser(floor=5.0)
    for t in range(0, 2000, 10):
        pulse = synth.apprehend(subject_mod.Impression("motion", t, 1070.0))
        assert pulse is None


def test_pulse_synthesiser_detects_single_pulse(env):
    import subject as subject_mod

    synth = subject_mod.PulseSynthesiser(floor=5.0)
    completed = []
    for t in range(0, 1000, 10):
        magnitude = 1070.0 + (80.0 if 300 <= t <= 400 else 0.0)
        pulse = synth.apprehend(subject_mod.Impression("motion", t, magnitude))
        if pulse is not None:
            completed.append(pulse)

    assert len(completed) == 1
    p = completed[0]
    assert p.mode == "motion"
    assert p.start_t == 300
    assert p.peak_t == 300
    assert p.peak == 1150.0


def test_expression_draws_sensor_bars_confidence_and_pleasure(env):
    import subject as subject_mod

    s = subject_mod.Subject()
    env.now_ms = 0
    env.motion = 1070 + 2394
    env.sound = 128
    env.light = 255
    subject_mod.affect(s.sensibility)
    next(s.active)

    assert [env.pixels[row][0] for row in range(5)] == [5, 5, 5, 5, 5]
    assert [env.pixels[row][2] for row in range(5)] == [5, 5, 5, 5, 5]
    assert [env.pixels[row][4] for row in range(5)] == [5, 5, 5, 5, 5]
    assert [env.pixels[row][1] for row in range(5)] == [0, 0, 0, 0, 0]
    assert [env.pixels[row][3] for row in range(5)] == [0, 0, 0, 0, 0]

    # Confidence builds bottom-up at 100% (9) and overwrites sensor pixels (5).
    s.understanding.schemas["motion"] = subject_mod.Schema("motion", 500, 1000, 2)
    s.expression.draw()
    assert [env.pixels[row][0] for row in range(5)] == [5, 5, 5, 9, 9]

    # At confidence 5, pleasure flashes the full column when expected_t falls due.
    s.understanding.schemas["motion"] = subject_mod.Schema("motion", 500, 1000, 5)
    env.now_ms = 950
    s.expression.draw()
    assert [env.pixels[row][0] for row in range(5)] == [0, 0, 0, 0, 0]

    env.now_ms = 1000
    s.expression.draw()
    assert [env.pixels[row][0] for row in range(5)] == [9, 9, 9, 9, 9]

    env.now_ms = 1079
    s.expression.draw()
    assert [env.pixels[row][0] for row in range(5)] == [9, 9, 9, 9, 9]

    env.now_ms = 1080
    s.expression.draw()
    assert [env.pixels[row][0] for row in range(5)] == [0, 0, 0, 0, 0]


def test_replay_motion_90bpm(env):
    pulses = [p for p in replay_csv(env, "jumping_90bpm.csv", "strength", "motion") if p.mode == "motion"]
    gaps = [b.peak_t - a.peak_t for a, b in zip(pulses, pulses[1:])]
    assert len(pulses) >= 10
    # 90 BPM corresponds to ~667 ms per beat.
    assert 550 <= statistics.median(gaps) <= 780, gaps


def test_replay_motion_150bpm(env):
    pulses = [p for p in replay_csv(env, "jumping_150bpm.csv", "strength", "motion") if p.mode == "motion"]
    gaps = [b.peak_t - a.peak_t for a, b in zip(pulses, pulses[1:])]
    assert len(pulses) >= 20
    # 150 BPM corresponds to ~400 ms per beat.
    assert 340 <= statistics.median(gaps) <= 460, gaps


def test_replay_baseline_datasets_produce_no_pulses(env):
    cases = (
        ("at_rest.csv", "strength", "motion"),
        ("near_silence.csv", "sound_level", "sound"),
        ("steady_light.csv", "light_level", "light"),
        ("low_ambient_noise.csv", "sound_level", "sound"),
    )
    for filename, col, mode in cases:
        pulses = [p for p in replay_csv(env, filename, col, mode) if p.mode == mode]
        assert pulses == [], (filename, pulses)


def test_equality_of_interval_steady_pulses_build_confidence(env):
    import subject as subject_mod

    rule = subject_mod.EqualityOfInterval("motion")
    assert rule.apply_rule(subject_mod.Pulse("motion", 0, 100, 1500), 120) is None

    exp1 = rule.apply_rule(subject_mod.Pulse("motion", 500, 600, 1500), 620)
    assert exp1.mode == "motion"
    assert exp1.interval == 500
    assert exp1.expected_t == 1100
    assert exp1.confidence == 0

    exp2 = rule.apply_rule(subject_mod.Pulse("motion", 1000, 1100, 1500), 1120)
    assert exp2.confidence == 1
    assert exp2.interval == 500
    assert exp2.expected_t == 1600

    exp3 = rule.apply_rule(subject_mod.Pulse("motion", 1500, 1620, 1500), 1640)
    assert exp3.confidence == 2
    assert exp3.interval == 510


def test_equality_of_interval_irregular_pulses_do_not_build_confidence(env):
    import subject as subject_mod

    rule = subject_mod.EqualityOfInterval("motion")
    times = [100, 600, 1500, 1800, 2700]
    exps = [rule.apply_rule(subject_mod.Pulse("motion", t - 20, t, 1500), t + 20) for t in times]
    assert all(e is None or e.confidence == 0 for e in exps)


def test_equality_of_interval_lapses_when_overdue(env):
    import subject as subject_mod

    rule = subject_mod.EqualityOfInterval("motion")
    rule.apply_rule(subject_mod.Pulse("motion", 0, 100, 1500), 120)
    exp = rule.apply_rule(subject_mod.Pulse("motion", 500, 600, 1500), 620)
    assert exp.expected_t == 1100

    # Still within tolerance (1100 + 0.2 * 500 = 1200)
    assert rule.apply_rule(None, 1150) is not None
    # Past deadline -> lapses
    assert rule.apply_rule(None, 1201) is None
    assert rule.confidence == 0


def max_confidence(env, filename, value_column, attr_name, mode):
    import subject as subject_mod

    s = subject_mod.Subject()
    best = 0
    with open(DATASETS / filename, newline="") as f:
        for row in csv.DictReader(f):
            env.now_ms = int(row["t_ms"])
            setattr(env, attr_name, float(row[value_column]))
            subject_mod.affect(s.sensibility)
            next(s.active)
            schema = s.understanding.schemas.get(mode)
            if schema is not None and schema.confidence > best:
                best = schema.confidence
    return best


def test_understanding_recognises_jumping_and_rejects_handling(env):
    import subject as subject_mod

    assert max_confidence(env, "jumping_90bpm.csv", "strength", "motion", "motion") >= 10
    assert max_confidence(env, "jumping_150bpm.csv", "strength", "motion", "motion") >= 20
    assert max_confidence(env, "everyday_handling.csv", "strength", "motion", "motion") < subject_mod.PLEASURE_CONFIDENCE


def test_understanding_recognises_sound_120bpm(env):
    cases = (
        ("sound_120bpm_short.csv", 7),
        ("sound_120bpm_1.csv", 38),
        ("sound_120bpm_2.csv", 52),
        ("sound_120bpm_3.csv", 58),
        ("sound_120bpm_wide.csv", 35),
        ("sound_120bpm_4.csv", 30),
    )
    for filename, min_conf in cases:
        assert max_confidence(env, filename, "sound_level", "sound", "sound") >= min_conf, filename


def test_understanding_anticipates_due_schema_once(env):
    import subject as subject_mod

    s = subject_mod.Subject()
    env.now_ms = 0
    _ = s.sensibility.t

    # Unconfirmed schema (confidence == 0) does not trigger anticipation.
    s.understanding.schemas["motion"] = subject_mod.Schema("motion", 500, 1000, 0)
    env.now_ms = 1000
    s.understanding.anticipate()
    assert s.understanding.anticipated == {}

    # Confirmed schema (confidence >= 1) fires once when now >= expected_t.
    s.understanding.schemas["motion"] = subject_mod.Schema("motion", 500, 1000, 1)
    env.now_ms = 999
    s.understanding.anticipate()
    assert s.understanding.anticipated == {}

    env.now_ms = 1000
    s.understanding.anticipate()
    assert "motion" in s.understanding.anticipated

    env.now_ms = 1010
    s.understanding.anticipate()
    assert s.understanding.anticipated == {}


def test_imagination_primed_by_schema_catches_softer_pulse_and_nudges_timing(env):
    import subject as subject_mod

    # A soft pulse (floor=20, amplitude=15) is missed without schema.
    synth_plain = subject_mod.PulseSynthesiser(floor=20.0)
    plain_pulses = []
    for t in range(0, 600, 10):
        mag = 1070.0 + (15.0 if 400 <= t <= 430 else 0.0)
        p = synth_plain.apprehend(subject_mod.Impression("motion", t, mag))
        if p is not None:
            plain_pulses.append(p)
    assert plain_pulses == []

    # With a high-confidence schema around t=410, the same soft pulse is caught and nudged toward 410.
    synth_primed = subject_mod.PulseSynthesiser(floor=20.0)
    schema = subject_mod.Schema("motion", 400, 410, 5)
    primed_pulses = []
    for t in range(0, 600, 10):
        mag = 1070.0 + (15.0 if 400 <= t <= 430 else 0.0)
        p = synth_primed.apprehend(subject_mod.Impression("motion", t, mag), schema=schema)
        if p is not None:
            primed_pulses.append(p)
    assert len(primed_pulses) == 1
    assert 400 < primed_pulses[0].peak_t <= 410


def test_pleasure_covers_one_missed_pulse_and_enforces_four_beat_cooldown(env):
    import subject as subject_mod

    s = subject_mod.Subject()
    rule = s.understanding.rules["motion"]

    # Build confidence to 5 (beats at 0, 500, 1000, 1500, 2000, 2500, 3000).
    for i in range(7):
        env.now_ms = i * 500
        s.imagination.pulses = [subject_mod.Pulse("motion", env.now_ms, env.now_ms, 1500)]
        s.understanding.judge()
    assert s.understanding.schemas["motion"].confidence == 5
    assert s.understanding.schemas["motion"].expected_t == 3500

    # Miss beat at 3500 -> Imagination fills it once overdue (3500 + 100 + 1 = 3601).
    env.now_ms = 3601
    s.imagination.synthesise()
    assert len(s.imagination.pulses) == 1
    assert s.imagination.pulses[0].peak_t == 3500
    s.understanding.judge()
    assert s.understanding.schemas["motion"].confidence == 5
    assert s.understanding.schemas["motion"].expected_t == 4000

    # Three real beats (4000, 4500, 5000) -> still within 4-beat cooldown (beats_since_miss == 3).
    for t in (4000, 4500, 5000):
        env.now_ms = t
        s.imagination.pulses = [subject_mod.Pulse("motion", t, t, 1500)]
        s.understanding.judge()
    assert s.understanding.schemas["motion"].confidence == 8

    # Miss beat at 5500 (only 3 real beats since last miss) -> resets confidence to 0.
    env.now_ms = 5601
    s.imagination.synthesise()
    assert s.imagination.pulses == []
    s.understanding.judge()
    assert "motion" not in s.understanding.schemas
    assert rule.confidence == 0

    # Rebuild to confidence 5, miss once, complete 4 real beats, then miss again -> allowed.
    for i in range(7):
        t = 6000 + i * 500
        env.now_ms = t
        s.imagination.pulses = [subject_mod.Pulse("motion", t, t, 1500)]
        s.understanding.judge()
    assert s.understanding.schemas["motion"].confidence == 5

    # First miss at 9500 covered.
    env.now_ms = 9601
    s.imagination.synthesise()
    s.understanding.judge()
    assert s.understanding.schemas["motion"].confidence == 5

    # Four real beats (10000, 10500, 11000, 11500).
    for t in (10000, 10500, 11000, 11500):
        env.now_ms = t
        s.imagination.pulses = [subject_mod.Pulse("motion", t, t, 1500)]
        s.understanding.judge()

    # Second miss at 12000 -> covered again after 4 real beats.
    env.now_ms = 12101
    s.imagination.synthesise()
    s.understanding.judge()
    assert s.understanding.schemas["motion"].confidence == 9
