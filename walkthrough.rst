====================================
A walk through the code step-by-step
====================================

At the entry-point, a ``Subject`` is created::

    if __name__ == "__main__":
        subject = Subject()

It's created along with its powers, i.e. the faculties::

    class Subject:

        def __init__(self):
            self.sensibility = Sensibility(self)
            self.imagination = Imagination(self)
            self.understanding = Understanding(self)

``Sensibility``'s ``__init__()`` creates a ``Manifold`` instance::

    class Sensibility:

        def __init__(self, subject):

            self.manifold = Manifold()

in which impressions will be received. ``Manifold.impressions`` is a dictionary; when populated it will contain a key for each sense and a corresponding ``Impression`` ``namedtuple`` as its value.

Filters are then created on Sensibility, one for each sensory mode:

.. code-block:: python
    :emphasize-lines: 4-8

    class Sensibility:
        def __init__(self, subject):
            ...
            self.filters = {
                "sound": LowPassFilter(AUDIO_CUTOFF),
                "motion": LowPassFilter(MOTION_CUTOFF),
                "light": LowPassFilter(LIGHT_CUTOFF),
            }

Each filter provides smoothing of sensory signals at the organic level.

Next, ``Subject`` creates its ``Imagination``, which sets up a ``PulseSynthesiser`` for each sensory mode:

.. code-block:: python
    :emphasize-lines: 4-8

    class Imagination:
        def __init__(self, subject):
            ...
            self.pulse_synthesisers = {
                "sound": PulseSynthesiser(time_constant=2000.0, k=2.3, floor=10.0),
                "motion": PulseSynthesiser(floor=15.0, min_impulse=2000.0),
                "light": PulseSynthesiser(),
            }

At present, we only admit of one kind of event: ``Pulse``. Each ``PulseSynthesiser`` is there to apprehend discrete events in that sense's stream of impressions, calibrated to the character of the sensor.

``Understanding`` is created next, with a rule for each sensory mode:

.. code-block:: python
    :emphasize-lines: 4-8

    class Understanding:
        def __init__(self, subject):
            ...
            self.rules = {
                "sound": EqualityOfInterval("sound"),
                "motion": EqualityOfInterval("motion"),
                "light": EqualityOfInterval("light"),
            }

A rule recognises a certain kind of formal pattern. ``EqualityOfInterval`` is currently the only rule we have, though any future rules will share the same shape.

``Subject`` also sets up ``Expression``, which communicates the internal states and judgements of the subject—via the built-in 5×5 display (one column per sense), and later over radio:

.. code-block:: python
    :emphasize-lines: 4

    class Subject:
        def __init__(self):
            ...
            self.expression = Expression(self)

At this point the Subject is fully assembled, according to the definitions in the code, but it is as it were static - it's not yet in motion. The next line:

.. code-block:: python
    :emphasize-lines: 4

    class Subject:
        def __init__(self):
            ...
            self.active = self.attend()

invokes ``Subject.attend()``, which contains the subject's existence and activity in time, in a Python generator that successively calls the key powers of each of the subject's faculties::

    def attend(self):
        """Running-time generator; steps the subject's powers once per next() call."""
        while True:
            self.imagination.synthesise()
            self.understanding.judge()
            self.understanding.anticipate()
            self.expression.draw()

            yield
