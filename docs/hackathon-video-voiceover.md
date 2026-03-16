# Hackathon Video Voiceover

## Main Version (75-90 seconds)

```text
The last time I got this excited about a new technology, it also became very expensive for me.

That taught me how quickly infrastructure cost and friction can add up when you use a powerful system a lot.

With AI, I do not want to make the same mistake again.

So I built RuleShield.

RuleShield is an optimization layer that sits in front of Hermes. It catches repetitive prompts before they hit the upstream LLM, tests candidate rules safely in shadow mode, and improves over time through feedback.

Here I am running Hermes through RuleShield and starting with a short health check to prove the proxy, agent path, and monitor are wired correctly.

Now I switch to a normal Hermes interaction.

The key idea is that RuleShield does not just blindly intercept. Some prompts should still go to the model, but repetitive prompts and recurring interaction patterns do not always need a full upstream call.

And when I want to inspect what is happening behind the scenes, I can cut to the monitor. That is where shadow mode becomes useful: candidate rules run in the background so we can compare what the rule would have returned against the real LLM response before promoting anything.

That gives Hermes a safe path to optimization: observe, compare, then promote only what looks trustworthy.

The feedback loop makes this more than a cache. Bad rules weaken, good rules get stronger, and over time Hermes gets a safer optimization layer.

And because Hermes can also be driven programmatically, the next step is not just intercepting prompts. It is shrinking recurring workflows themselves, including future cron-style optimizers that split work into deterministic pre-processing, a smaller core prompt, and deterministic post-processing.

RuleShield helps Hermes reduce repetitive LLM spend today, and gives it a path toward safer self-optimization tomorrow.
```

## Short Version (45-60 seconds)

```text
The last time I got this excited about a new technology, it also became very expensive for me.

That taught me how quickly infrastructure cost and friction can add up when you use a powerful system a lot.

With AI, I do not want to make the same mistake again.

So I built RuleShield.

RuleShield sits in front of Hermes and intercepts repetitive prompts before they hit the upstream LLM.

What makes it different is shadow mode: candidate rules can run safely in the background, so we compare them against real LLM responses before promoting anything live.

That gives Hermes a safe path to optimization instead of just a static rule list.

In the normal Hermes flow, the user just sees the agent working. In the monitor, we can see what would trigger, what actually triggered, and how RuleShield is learning over time.

The feedback loop then strengthens good rules and weakens bad ones over time.

And because Hermes can also be driven through the Python API, this can grow beyond prompt interception into workflow optimization for recurring tasks and cron-style automations.

RuleShield helps Hermes save money now, and build a safer optimization layer over time.
```

## Optional Mid-Monitor Lines

Use these only if the final edit includes the mid-video Test Monitor cut.

```text
The normal Hermes interaction is what the user sees.

This monitor is what RuleShield sees behind the scenes.

Here we can watch candidate rules in shadow mode, see what would have triggered, what actually triggered, and use that to decide what is safe to promote.
```
