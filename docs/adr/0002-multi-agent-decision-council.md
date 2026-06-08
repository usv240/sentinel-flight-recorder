# ADR-0002: Four agents arguing in the open, not one agent handing down a verdict

**Status:** Accepted
**Date:** 2026-05-25

---

Early experiments had a single Gemini call read the live metrics and respond with a recommendation: "Don't raise prices, NPS is too low." It was accurate. It was also the kind of advice a founder under quarterly pressure can shrug off in five seconds, because there's nothing in it to engage with, just a verdict from a black box. "The AI says no" carries about as much weight as "my cofounder says no" once you've already half-decided to do it anyway.

The problem isn't accuracy. It's that a single verdict gives you nothing to push against. You can't tell whether the model weighed the upside, considered alternatives, or just pattern-matched "low NPS plus price increase equals bad." There's no reasoning to interrogate, so there's nothing to actually trust either. You're just substituting one unexplained opinion for another.

The fix was to stop asking for a verdict and start asking for a debate. SENTINEL convenes four Gemini agents with genuinely different jobs:

- **Data Agent** reports only what the live Fivetran metrics actually say: numbers and trends, no opinion
- **Risk Agent** is told to find every reason this could go wrong, scored against historical patterns and the Bradford Hill signal
- **Alternatives Agent** has to propose three different, concrete paths forward. It isn't allowed to simply say "don't"
- **Lead Agent** reads what the other three produced and makes the final call, citing their reasoning by name

All four post into the same Slack thread where the decision is already being discussed, in the order they finish, so the people making the call watch the reasoning assemble in real time the way they'd watch colleagues debate it in a meeting. They can see exactly where the agents agree, where they don't, and why.

The honest cost: four model calls instead of one, and a slower reply (the full council typically lands within 60 seconds rather than instantly). We think that's a fair price for turning "the AI said no" into "here's specifically what it saw, what it's worried about, and what else you could do instead. Now you decide."
