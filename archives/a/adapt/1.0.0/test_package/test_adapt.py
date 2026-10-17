#!/usr/bin/env python3
"""Exercise Adapt's public intent registration and determination API."""

from adapt.engine import IntentDeterminationEngine
from adapt.intent import IntentBuilder


engine = IntentDeterminationEngine()
engine.register_entity("play", "PlayVerb")
engine.register_entity("the big bang theory", "Television Show")
engine.register_intent_parser(
    IntentBuilder("play television intent")
    .require("PlayVerb")
    .require("Television Show")
    .build()
)

results = list(engine.determine_intent("play the big bang theory"))
assert results, "Adapt returned no intent for registered vocabulary"
intent = results[0]
assert intent["PlayVerb"] == "play"
assert intent["Television Show"] == "the big bang theory"
assert intent["confidence"] > 0.0
print("adapt 1.0.0 intent determination: PASS")
