# Tournament Realism Review

This review checks whether the generated v2 predictions look plausible as a full tournament forecast, not just as individual model rows.

## Current Output

- Group matches: 72
- Knockout matches: 32
- Champion: Spain
- Runner-up: Argentina
- Third place: France
- Fourth place: Brazil

The model still predicts Colombia vs Portugal as a `1-1` draw, which is more internally consistent than the earlier hard-reconciled Colombia `1-0` win.

## Group Stage

Group-stage result distribution:

| Result | Matches | Share |
| --- | ---: | ---: |
| Home win | 42 | 58.3% |
| Draw | 22 | 30.6% |
| Away win | 8 | 11.1% |

Most common group scorelines:

| Score | Matches |
| --- | ---: |
| 1-0 | 22 |
| 1-1 | 21 |
| 2-0 | 18 |
| 0-2 | 6 |
| 0-0 | 1 |

The selected scorelines are low scoring, with a mean of `1.69` goals per group match. This is mostly a score-selection effect: exact-score modes from Poisson-style models are conservative and often sit below the mean of the full goal distribution. This is not automatically a bug because exact-score forecasts are supposed to pick the most likely individual score, not reproduce the full tournament goal average.

## Tiebreak Review

The original bracket used alphabetical team names when group teams were tied on points, goal difference, and goals for. That created an unrealistic Group L result where Croatia finished above England despite an exact tie.

The prediction pipeline now uses model tiebreak strength for unresolved group and best-third ties. Group L is now:

| Rank | Team | Points | GD | GF |
| ---: | --- | ---: | ---: | ---: |
| 1 | England | 5 | 2 | 4 |
| 2 | Croatia | 5 | 2 | 4 |
| 3 | Panama | 5 | 2 | 4 |
| 4 | Ghana | 0 | -6 | 0 |

This is still a model proxy. The real tournament could use fair-play points or drawing lots if official tiebreakers remain exhausted, but model strength is more defensible than alphabetical order for a prediction project.

## Notable Group Outcomes

Group winners that are not the strongest team in their group by the composite strength check:

| Group | Winner | Strongest Team | Strongest Finish |
| --- | --- | --- | ---: |
| D | USA | Turkiye | 2 |
| E | Ecuador | Germany | 2 |

Best eliminated teams by composite strength:

| Team | Group | Finish | Points |
| --- | --- | ---: | ---: |
| Algeria | J | 3 | 2 |
| Australia | D | 4 | 1 |
| Côte d'Ivoire | E | 3 | 2 |
| Scotland | C | 3 | 2 |

These are plausible enough to leave model-driven. They are not bracket-breaking anomalies.

## Knockout Stage

Final four:

| Match | Result | Winner |
| --- | --- | --- |
| Semi-final | Brazil 1-1 Spain | Spain on penalties |
| Semi-final | France 1-1 Argentina | Argentina on penalties |
| Third-place playoff | Brazil 1-1 France | France on penalties |
| Final | Spain 1-1 Argentina | Spain on penalties |

The knockout stage has 12 penalty shootouts across 32 matches. That is high, but it follows from the same conservative exact-score selector that produces many `1-1` predictions for close elite-team matchups. Since knockout penalty prediction is worth only a small separate scoring component, the current approach is acceptable for this pass.

## Recommendation

Do not manually override the bracket. After the strength tiebreak fix, the tournament path is coherent enough to keep as model output.

The main remaining modeling question is whether to replace pure scoreline likelihood with an expected competition-points selector. A scratch check showed that such a selector may improve partial score and outcome utility, but it can reduce exact-score accuracy. Since the current holdout exact-score accuracy is above the stretch target, leave the score selector unchanged for now.
