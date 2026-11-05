# Synthetic apparatus visual feedback v1

This optional profile adds an engineered indicator-light sensor to the gym.
It is not a claim that biological visual neurons specialize in bench presses or
curls. Official IDs, transmitter calls, circuit edges, neural dynamics and motor
readout are unchanged. The baseline profile `none`, original recorded bench run
and fixed-budget comparison remain unchanged.

An attached bench has its stronger indicator on the fly's left visual channel;
an attached curl station has it on the right. These are authored apparatus
indicators, shown as lamps in the scene. For normalized actual joint position q
and load in model force units:

```
brightness = 0.16 + 0.35*clamp(q,0,1) + 0.15*clamp(load/3,0,1)
brightness *= 0.35 during apparatus recovery
bench: indicator_left=brightness, indicator_right=0.25*brightness
curl: indicator_left=0.25*brightness, indicator_right=brightness
detached or profile none: both indicators=0
```

The existing food vision is retained. Each visual input is the maximum of its
food reading and apparatus indicator. The existing sensory adapter feeds that
bounded value into the current compact circuit's official `vision_left`/
`vision_right` L2 inputs. This is
a synthetic physical light cue, not proprioception, neural injection from the
browser, a new connection or an invented brain region. A bright food cue can
dominate it. Downstream differences are reported only when the model produces
them; motor drive may still saturate from the separate gym odor paths.

The indicator sample is latched before `brain.step` and sent with the exact
simulation step that used it. It is not recomputed after equipment integration.
Pause holds that sample. Setup while paused changes the imposed body/station
state, while new visual input is sampled on the next model step. No render time
or synthetic spike event is used.

Exercise selection is explicit experimental setup. A target station is reserved
while the request waits for the current joint to reach bottom with zero velocity.
Then Python positions the fly at the station's recorded pose and starts two
seconds of supported recovery. Lifetime repetitions, sets, positive work,
fatigue and already completed repetitions within the current set are preserved.
A partial return does not count. Setup is not locomotion or a learned equipment
choice, and adds no work or reward. A fully occupied target kind is rejected.

The new demonstration recordings and measured input/rate agreement are in
[EXERCISES.md](../drosolift/EXERCISES.md). The original profile `none` is guarded
by exact reproduction of every frame in the original bench calibration sample.
