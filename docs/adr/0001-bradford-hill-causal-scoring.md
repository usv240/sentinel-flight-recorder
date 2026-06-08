# ADR-0001: Score causation with Bradford Hill, not a bare correlation number

**Status:** Accepted
**Date:** 2026-05-22

---

The first version of the causal tracer reported a single Pearson correlation coefficient between a decision date and a metric's later movement. It worked, technically. It was also exactly the kind of number that gets people in trouble: a correlation of 0.81 *sounds* authoritative, but it doesn't tell you whether the relationship is real, whether it could be coincidence, whether the metric was already trending that way before the decision, or whether something else entirely caused both.

That's the core problem with handing someone a single statistic and calling it an answer. It hides precisely the kind of doubt a careful person would want to see before betting a business decision on it.

Two other approaches were considered. Reporting just a p-value has the same issue: it's still one number standing in for a judgment call. Running a single "best" statistical test and showing only its result just moves the arbitrary choice up one level, because which test is "best" depends on the shape of the data, and pre-committing to one means you might be picking the one that happens to agree with you.

So the causal tracer runs three independent tests instead: Granger causality, interrupted time series, and Mann-Whitney U, each of which looks at a *different* kind of evidence (does timing predict the outcome, did the trend change right at the decision point, are the before-and-after values actually distinguishable distributions). Their results then feed into the Bradford Hill framework: nine separate criteria (strength, consistency, specificity, temporality, dose-response, plausibility, coherence, experimental evidence, and analogy), each scored on its own and combined into a single 0 to 100% "causal strength" figure with a plain-English label: Strong, Moderate, Weak, or Insufficient.

Bradford Hill has been the standard for arguing that smoking causes cancer, that a drug causes a side effect, that a chemical causes an illness, for sixty years now, in contexts where "it's just a correlation" is a matter of life and death, not a quarterly slide. Nobody had pointed it at ordinary business decisions before. It turns out the underlying problem is identical: *did this one thing really cause that other thing, in a messy real-world dataset where you can't run a controlled experiment?*

The honest tradeoff: nine criteria plus three statistical tests is more to compute and more to explain than a single number. We think that's the right trade. A score you can interrogate is worth more than a score you have to take on faith.
