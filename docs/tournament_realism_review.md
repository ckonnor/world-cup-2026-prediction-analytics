# Tournament Realism Review

This review checks whether the generated v2 predictions look plausible as a full tournament forecast, not just as individual model rows.

## Current Output

- Group matches: 72
- Knockout matches: 32
- Champion: Spain
- Runner-up: Argentina
- Third place: Brazil
- Fourth place: Netherlands
- Global scoreline blend: `0.39`

The model still predicts Colombia vs Portugal as a `1-1` group-stage draw, which is internally consistent with both teams advancing from Group K. The final is Spain `1-1` Argentina, with Spain winning on penalties.

## Group Stage

Group-stage result distribution:

| Result | Matches | Share |
| --- | ---: | ---: |
| Home win | 48 | 66.7% |
| Draw | 20 | 27.8% |
| Away win | 4 | 5.6% |

Most common group scorelines:

| Score | Matches |
| --- | ---: |
| 1-0 | 28 |
| 2-0 | 18 |
| 1-1 | 16 |
| 0-0 | 4 |
| 0-2 | 2 |

The selected scorelines are low scoring, with a mean of `1.53` goals per group match. This is mostly a score-selection effect: exact-score modes from Poisson-style models are conservative and often sit below the mean of the full goal distribution. This is acceptable for an exact-score competition because the task is to choose the most likely individual scoreline, not reproduce tournament goal averages.

## Tiebreak Review

The original bracket used alphabetical team names when group teams were tied on points, goal difference, and goals for. The prediction pipeline now uses model tiebreak strength for unresolved group and best-third ties.

Group L now has a cleaner ordering:

| Rank | Team | Points | GD | GF |
| ---: | --- | ---: | ---: | ---: |
| 1 | England | 7 | 3 | 5 |
| 2 | Croatia | 4 | 1 | 4 |
| 3 | Panama | 3 | 0 | 2 |
| 4 | Ghana | 1 | -4 | 0 |

This is still a model proxy. The real tournament could use fair-play points or drawing lots if official tiebreakers remain exhausted, but model strength is more defensible than alphabetical order for a prediction project.

## Notable Group Outcomes

Ecuador wins Group E over Germany despite Germany having the stronger dashboard composite profile. This is the main group-stage upset in the `0.39` forecast and is plausible enough to leave model-driven.

Best eliminated teams by composite strength:

| Team | Group | Finish | Points |
| --- | --- | ---: | ---: |
| Senegal | I | 3 | 3 |
| Iran | G | 4 | 3 |
| Australia | D | 3 | 3 |
| Egypt | G | 3 | 3 |
| Algeria | J | 3 | 2 |
| Panama | L | 3 | 3 |

These are plausible enough to leave model-driven. Senegal missing out from a difficult France/Norway group is the most notable call, but not a bracket-breaking anomaly.

## Knockout Stage

Final four:

| Match | Result | Winner |
| --- | --- | --- |
| Semi-final | Brazil 1-1 Spain | Spain on penalties |
| Semi-final | Netherlands 1-1 Argentina | Argentina on penalties |
| Third-place playoff | Brazil 1-0 Netherlands | Brazil |
| Final | Spain 1-1 Argentina | Spain on penalties |

The knockout stage now has 9 penalty shootouts across 32 matches, or `28.1%`. That is still much closer to the historical World Cup knockout benchmark than the prior 11-shootout version, while avoiding the colder `1-0` final produced by the `0.40` setting.

## Recommendation

Keep the global `0.39` scoreline blend for final publication. It improves blended holdout outcome accuracy from `62.6%` to `63.1%`, keeps exact-score accuracy above the stretch target at `14.7%`, and is the best compromise between historical penalty frequency and a believable final scoreline.
