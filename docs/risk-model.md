# Risk methodology

## Supply-chain prioritization: weighted-v1

This is a transparent operational prioritization heuristic, not a calibrated probability of damage or production loss. Scores apply to a supplier-part-factory dependency at an explicit UTC as-of date.

`score = 30E + 25I + 20S + 15L + 10C`

Each input is clamped to `[0,1]`:

| Factor | Definition |
|---|---|
| E: environmental | Maximum active-event severity × distance attenuation across origin, destination and applicable shipment hub |
| I: inventory | `max(0, 1 - days_of_supply / max(safety_stock_days, 1))` |
| S: sourcing | 1 if there is no other approved active supplier; otherwise 0 |
| L: replenishment | `max(0, 1 - days_of_supply / max(lead_time_days, 1))` |
| C: criticality | Supplier business criticality / 5 |

Thresholds are LOW `[0,25)`, MODERATE `[25,50)`, HIGH `[50,75)`, CRITICAL `[75,100]`. Each assessment stores normalized inputs, weights, point contributions, associated event, distance, coverage and model version. Missing inventory produces INCOMPLETE when consumption is positive. No current consumption removes inventory and lead-time pressure; it does not erase environmental or sourcing exposure.

### Environmental rules

Haversine distance uses mean Earth radius 6371.0088 km, with antimeridian and antipodal cases tested. Earthquake severity is `clamp((magnitude - 4) / 2.5)` and attenuation is `clamp(1 - distance / 300km)`. Earthquake exposure lasts seven days. Depth is preserved but is not a calibrated attenuation input.

Weather severity is the largest of `clamp((wind_kmh-60)/60)`, `clamp((precipitation_mm-10)/30)`, and `clamp((temperature_c-38)/12)`. Weather attenuation extends to 100 km and expires after 24 hours. These thresholds identify investigation candidates; Open-Meteo current precipitation represents the provider's current interval and is not silently treated as a daily total.

The most severe current exposure determines E, avoiding double-counting related events. Alternative scoring, regional thresholds and scientifically calibrated ShakeMap exposure can be introduced as new model versions.

### Inventory estimates

Days of supply is snapshot quantity / configured average daily usage. The UI states snapshot date; coverage is not a live warehouse count. Projected stockout adds eligible in-transit shipment quantities only if their arrival precedes current exhaustion. Delayed, delivered, overdue and post-stockout shipments do not prevent the initial stockout. Usage is held constant and production mix is not modeled.

### Reproducible scenarios

- `GM-10000` has 3.8 days of stock, a 45-day source lead time, criticality 5 and no alternative. A simulated M6.2 event approximately 15 km from its supplier pushes the weighted score above 75.
- The Gulf hub has a simulated high-wind event. Routed shipments are explicitly seeded delayed, and their destination dependencies inherit environmental exposure.
- Aster E4 steering reports rise from 35 per month to 104 in the last completed month.

## Automotive detection: rolling-v1

Evaluate the last **completed** calendar month. Use the previous 12 completed months, including zero-count months only where dataset history is established. Set `mu = mean(baseline)` and `sigma = max(population_stddev(baseline), sqrt(max(mu,1)))`.

Flag only when `observed >= 10` and `observed > max(2*mu, mu+3*sigma)`. HIGH is the default flagged severity; CRITICAL requires at least twice the detection threshold. Percentage increase is null when baseline mean is zero. Recalculation replaces the selected month's signals and preserves other months.

The live baseline begins at the earliest available complaint, a conservative coverage proxy rather than a guarantee of complete historical reporting. Reporting delays, media attention, recall publicity and fleet size confound complaint counts. Signals warrant investigation; they do not establish defects or fleet-adjusted risk. The current partial month may appear in volume charts but is excluded from detection.

## Narrative rules: keywords-v1

Lowercase, normalize punctuation and whitespace, then match whole-word keywords/phrases. Multiple categories are allowed. Unmatched text is UNCATEGORIZED. Store matches and rule version alongside the preserved original narrative. Rules do not handle negation or prove causality; there is no paid AI or implicit ML claim.
