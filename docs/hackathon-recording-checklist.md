# Hackathon Recording Checklist

## Before Recording

- verify gateway starts cleanly
- verify dashboard starts cleanly
- open `http://localhost:5174/test-monitor`
- choose one stable model/provider profile
- make sure the selected profile shows only the intended scripts
- clear distracting old runs if needed
- prepare one backup screenshot of:
  - active run
  - finished run with savings visible
  - docs or slides opening frame

## Recommended Terminal Prep

Run in advance:

```bash
ruleshield init --hermes
ruleshield start
```

If needed, separately start the dashboard dev server.

## Recommended Demo Run Order

1. show `ruleshield init --hermes`
2. show `ruleshield start`
3. open `/test-monitor`
4. run health check
5. run Hermes user scenario
6. keep `RuleShield Live` visible for the payoff
7. close with future direction

## Optional Alternative Cut

If time allows and the monitor is behaving well:

- record the main demo as a normal Hermes interaction first
- then insert a mid-video cut to `/test-monitor`
- use that segment to explain shadow mode, would-trigger, triggered rules, and safe rollout

Keep this as a support segment, not the main narrative.

## What To Watch During Recording

- active run status updates
- prompt/response log visibly updating
- `RuleShield Live` panel staying readable
- `Would Trigger (Shadow)` not showing unrelated historic totals
- `Triggered Rules` and `Run Savings` visible after the run

## If Something Breaks Live

- do not debug on camera for long
- switch to a known-good finished run
- use backup screenshots if needed
- keep the narration focused on the value, not the glitch

## Before Posting

- export final video
- verify audio is understandable
- verify the tweet includes `@NousResearch`
- attach the demo video
- post the tweet
- paste the tweet link into the Discord submissions channel

## Final Assets

- [hackathon-video-voiceover.md](./hackathon-video-voiceover.md)
- [hackathon-tweet-draft.md](./hackathon-tweet-draft.md)
- [hackathon-discord-submission.md](./hackathon-discord-submission.md)
- [hermes-hackathon-demo-blueprint.md](./hermes-hackathon-demo-blueprint.md)
- [hermes-hackathon-plan.md](./hermes-hackathon-plan.md)
