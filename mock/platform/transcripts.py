"""Deterministic fake transcripts. Returned no matter what URL is requested.

Each transcript has segments with start/end seconds and text. They are
intentionally written to contain one very obvious dramatic crescendo so a
correct LLM step has something to lock onto.
"""

DEFAULT_TRANSCRIPT = {
    "video_id": "ds-001",
    "title": "I Spent 24 Hours Inside An Abandoned Theme Park",
    "duration_seconds": 240,
    "language": "en",
    "segments": [
        {"start": 0, "end": 8, "text": "What's up guys, today we're doing something I've never done before."},
        {"start": 8, "end": 18, "text": "We're spending twenty four hours inside this completely abandoned theme park."},
        {"start": 18, "end": 30, "text": "I've got my whole team with me, we've got cameras, we've got snacks, let's just see what happens."},
        {"start": 30, "end": 45, "text": "So we just got dropped off at the front gate. The place is huge. It hasn't been open in fifteen years."},
        {"start": 45, "end": 60, "text": "Walking through the entrance, you can see the old ticket booth, the rides are still here, just rusted over."},
        {"start": 60, "end": 75, "text": "Okay so we've been here a couple hours. Things have been pretty chill. Just exploring, taking photos."},
        {"start": 75, "end": 90, "text": "Wait. Wait wait wait. Did you guys hear that? Stop. Everybody stop. Listen."},
        {"start": 90, "end": 105, "text": "OH MY GOD. The Ferris wheel just started moving. By itself. There is no power here. There is no power."},
        {"start": 105, "end": 120, "text": "I am literally watching this thing turn. This is the craziest thing I have ever seen in my entire life."},
        {"start": 120, "end": 135, "text": "Okay we are running. We are running back to the entrance. I do not care what that was. We are leaving."},
        {"start": 135, "end": 150, "text": "Alright we're back at the gate. We've calmed down a bit. Still no explanation for what we just saw."},
        {"start": 150, "end": 170, "text": "We decided to push through and finish the night. The team voted, three to one. I was the one."},
        {"start": 170, "end": 195, "text": "Couple more hours of nothing happening, just normal abandoned park stuff, broken glass, weird smells."},
        {"start": 195, "end": 220, "text": "Sun's coming up now. We made it. Twenty four hours done. Honestly the Ferris wheel thing was probably wind."},
        {"start": 220, "end": 240, "text": "If this video gets a million likes I'll come back and stay another night. Subscribe so you don't miss it."},
    ],
}
