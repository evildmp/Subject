===========
Development
===========

How tests work
==============

The test suite runs under desktop Python using ``pytest`` rather than on the micro:bit hardware.

Hardware and clock stubs
------------------------

``subject.py`` depends on MicroPython's ``microbit`` module, ``time.ticks_ms()``. A shared ``pytest`` fixture in ``testing/`` provides:

* A fake ``microbit`` module registered in ``sys.modules["microbit"]`` with controllable ``microphone.sound_level()``, ``accelerometer.get_strength()``, ``display.read_light_level()``, ``temperature()``, and a 5x5 ``display`` buffer for inspecting ``Expression`` output.
* A controllable millisecond clock patched onto ``time.ticks_ms`` and ``time.ticks_diff`` so tests advance ``Sensibility.t`` deterministically without real-time waiting.

Unit and dataset replay tests
-----------------------------

* **Unit tests** exercise ``Subject``, ``Sensibility`` (``Manifold`` and ``LowPassFilter``), ``PulseSynthesiser``, ``EqualityOfInterval`` (``apply_rule()``), ``Understanding``, and ``Expression`` against synthetic inputs (quiet baselines, single pulses, steady/irregular intervals, overdue lapse, and display output).
* **Dataset replay tests** read recorded CSV files from ``datasets/``, set the fake clock to each row's ``t_ms``, feed samples through ``affect()`` and ``next(subject.active)``, and check detected pulses and ``Understanding`` confidence against beat tempos, handling, and baseline silence/rest expectations:

  * Tempo and handling checks (``test_replay_motion_90bpm``, ``test_replay_motion_150bpm``, ``test_understanding_recognises_jumping_and_rejects_handling``):

    * ``jumping_90bpm.csv``
    * ``jumping_150bpm.csv``
    * ``everyday_handling.csv``

  * Baseline zero-pulse checks (``test_replay_baseline_datasets_produce_no_pulses``):

    * ``at_rest.csv``
    * ``near_silence.csv``
    * ``steady_light.csv``
    * ``low_ambient_noise.csv``

Dataset formats
---------------

Raw sensor datasets in ``datasets/`` record sensor values with timestamps; the CSV files have a ``t_ms,<sensor>`` header:

* ``t_ms``: elapsed milliseconds since capture start.
* ``strength``: ``microbit.accelerometer.get_strength()``.
* ``sound_level``: ``microbit.microphone.sound_level()``.
* ``light_level``: ``microbit.display.read_light_level()``.

How to run tests
================

Create and activate a virtual environment, then install the development dependencies::

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"

Run the test suite from the repository root::

    pytest -v

Flashing the micro:bit
======================

The most convenient way to flash the micro:bit will often be (with the virtual environment activated of course)::

    mpremote fs cp subject.py :main.py + reset

This copies ``subject.py`` to ``main.py`` on the micro:bit and resets it.
