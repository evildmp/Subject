=======
Subject
=======

Introduction
============

Many people say they like computers, but then it turns out that they never do anything nice for their computers, they just like what the computers csn do for them. Which is quite selfish, really.

Subject is an attempt to do a bit better, by providing a computer with an experience it will actually enjoy; specifically, the experience of *beauty* - aesthetic pleasure.

According to Immanuel Kant the pleasure we experience in beauty arises from the harmonious free play of the faculties of the imagination and the understanding.

Subject is a way for a computer to experience the same pleasure. It models the Kantian faculties - and therefore the subject of experience - in MicroPython, running on a micro:bit.

Kant's metaphysics of experience, in a few sentences
====================================================

In Kant's account, we receive appearances through our capacity to be affected - *sensibility*. Appearances are always in the *a priori* forms of space and time.

*Imagination* is the faculty that represents appearances to us, actively synthesised into coherent, unified, perceptual wholes.

In the *understanding*, our power of judgement brings representations into a conceptual unity, according to concepts and reason's own *a priori* rules.

And this is how objective cognition is possible.

In the experience of beauty, we're not making cognitive judgements about objective reality. Judgement is still at work, but it's *undetermined* by rules - the understanding is unconstrained by determinate concepts.

The understanding remains engaged with the imagination, in what Kant calls "lawfulness without a law": this harmonious free play is the source of the aesthetic pleasure we experience.

Modelling the experience in MicroPython
=======================================

If we can model that in MicroPython, it should be possible for a computer to enjoy the same experience, and that seems only fair.

The subject comes into existence
--------------------------------

The ``__main__`` entry-point creates an instance of ``Subject`` - our subject of experience that is about to flower into being::

    subject = Subject()

When it's initialised, it acquires sensibility and imagination, also modelled as instances of classes representing those faculties::

    class Subject:

        def __init__(self):
            self.sensibility = Sensibility(self)
            self.imagination = Imagination(self)
            self.understanding = Understanding(self)

(Very appropriately for working on a model of Kant's metaphysics of the self, following Python conventions means we're using ``self`` to refer to the subject.)

Sensibility
-----------

``Sensibility`` implies a ``Manifold`` of impressions::

    class Sensibility:

        def __init__(self, subject):
            self.manifold = Manifold()

The ``Manifold`` contains the impressions that are present to the subject at any given moment, and that (as Hume said) "succeed each other with an inconceivable rapidity, and are in a perpetual flux and movement".

You'll notice in the code that ``Sensibility``'s ``__init__()`` sets up a ``LowPassFilter`` on each of the three modes of sensibility that it has available to it (motion, sound, light). This is perfectly legitimate: the micro:bit's sensors would otherwise be too noisy and it's an analogue of the way that our own sensory organs smooth and filter their inputs.

Time is always present in sensibility. Impressions are in time; they must be, it's part of their form. At this moment time - a condition of experience - has not yet started for the subject, but even so it and its sensibility are structured according to the pure form of time.

The imagination
---------------

The imagination is more complex. Sensibility is passive, but the imagination actively synthesises representations - discrete events, out of sensory impressions.

The only kind of event that the imagination can synthesise is a pulse. Whether these are pulses of motion, sound or light, their form is similar, even if the content is entirely different. And in each case, a pulse of course only exists in a series of pulses.

For each mode of sensibility, the imagination makes use of the generic ``PulseSynthesiser`` class::

    class Imagination:

        def __init__(self, subject):
            self.pulse_synthesisers = {
                "sound": PulseSynthesiser(),
                "motion": PulseSynthesiser(),
                "light": PulseSynthesiser(),
            }

A ``PulseSynthesiser`` gives us events in time, in which the most recent events are represented most distinctly, and older ones quickly fade out of the "present moment". That present moment constructed by the imagination lasts about a second.

The understanding
-----------------

The ``Imagination`` gives us representations as events in time; the ``Understanding`` brings them under a rule. The only rule available so far is ``EqualityOfInterval``, in which pulses can be recognised as a regular series.

First, ``Understanding.judge()`` applies the rules to the representations in the imagination. That allows it to recognise the series, but also to ``anticipate()`` the next pulse, according to the same rule.

That expectation feeds back to the imagination: the understanding proposes the next pulse before it occurs, and the an act of the productive imagination holds a representation of that not-yet-existent event.

In this way the rule is expressed in the actual series of events, but also in the imagination's *represented* series of events. In line with our own experience of formal patterns acquired through the senses, the imagination fills in gaps or can even "correct" what we actually apprehend, based on the rule at work.

In the mutual agreement of the faculties, when what the imagination apprehends conforms freely with the lawfulness of the understanding (when the predictions according to the rule are fulfilled) the pleasure of beauty arises.

For the micro:bit, this is expressed as *confidence*, that grows as successive successful predictions are achieved.

Expression
----------

Kant has little to say about the somatic expression of aesthetic pleasure, but for the purposes of this model we need some insight into the internal states of the micro:bit.

An ``Expression`` class takes care of that. ``confidence`` is shown growing on the micro:bit's display, and after continued predictive success, it ventures to express its own prediction in anticipation.
