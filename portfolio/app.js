'use strict';
const steps = [
    ['EVENT EVIDENCE', 'A nearby earthquake creates exposure.', 'A simulated M6.2 earthquake occurs near Hsinchu on 17 September 2026. The semiconductor supplier site is approximately 15 km away. Proximity indicates exposure, not confirmed damage.', 'Distance to supplier', '15 km', 'Source: bundled synthetic scenario. No damage or delivery interruption has been independently confirmed.'],
    ['PRODUCTION DEPENDENCY', 'One component connects two continents.', 'Taiwan Precision Semiconductors supplies GM-10000, a steering control semiconductor, to Fremont Manufacturing. The factory consumes 100 units per day. The current approved source has a 45-day replenishment lead time.', 'Approved alternative suppliers', '0', 'The supplier and factory are fictional. This is a modeled dependency, not a claim about a real manufacturer.'],
    ['INVENTORY EVIDENCE', 'Coverage is shorter than replenishment.', 'The 18 September inventory snapshot contains 380 units: 3.8 days at current consumption. A shipment due seven days later does not arrive before estimated exhaustion. The application estimates stockout on 21 September 2026.', 'Coverage / current lead time', '3.8 / 45 days', 'Stockout is an estimate based on a fixed consumption rate. Actual deliveries, usable stock and production schedules must be confirmed.'],
    ['SOURCING DECISION', 'A candidate is not yet a usable alternative.', 'Stuttgart Motion 08 offers a modeled 28-day lead time with a 12% premium over the part base cost. Qualification is pending and capacity is unknown. Confirm current supplier status, reconcile inbound inventory, and escalate the qualification gap to sourcing.', 'Candidate qualification', 'Pending', 'A shorter lead time still exceeds 3.8 days of coverage. No purchase or supplier contact is initiated by this sample.']
];
let active = 0;
function showStep(index) {
    active = index;
    const ids = ['step-label', 'step-title', 'step-body', 'fact-label', 'fact-value', 'step-note'];
    ids.forEach((id, i) => { document.getElementById(id).textContent = steps[index][i]; });
    document.querySelectorAll('.step').forEach((button, i) => {
        button.classList.toggle('active', i === index);
        button.setAttribute('aria-pressed', String(i === index));
    });
    document.getElementById('next-step').textContent = ['Next: the dependency →', 'Next: the inventory →', 'Next: the options →', 'Start again ↺'][index];
}
document.querySelectorAll('.step').forEach(button => button.addEventListener('click', () => showStep(Number(button.dataset.step))));
document.getElementById('next-step').addEventListener('click', () => showStep((active + 1) % 4));
const coverage = document.getElementById('coverage');
const alternative = document.getElementById('alternative');
function recalculate() {
    const days = Number(coverage.value);
    document.getElementById('coverage-value').textContent = `${days.toFixed(1)} days`;
    const factors = [
        ['Environment', 0.8373 * 30, 30], ['Inventory', Math.max(0, 1 - days / 14) * 25, 25],
        ['Sourcing', alternative.checked ? 0 : 20, 20], ['Lead time', Math.max(0, 1 - days / 45) * 15, 15], ['Criticality', 10, 10]
    ];
    const total = factors.reduce((sum, row) => sum + Math.round(row[1] * 100) / 100, 0);
    const severity = total >= 75 ? 'CRITICAL' : total >= 50 ? 'HIGH' : total >= 25 ? 'MODERATE' : 'LOW';
    document.getElementById('score').textContent = total.toFixed(1);
    document.getElementById('severity').textContent = severity;
    const container = document.getElementById('factors');
    container.replaceChildren();
    factors.forEach(([name, value, weight]) => {
        const row = document.createElement('div'); row.className = 'factor';
        const label = document.createElement('span'); label.textContent = name;
        const meter = document.createElement('meter'); meter.min = 0; meter.max = weight; meter.value = value; meter.setAttribute('aria-label', `${name}: ${value.toFixed(1)} of ${weight} points`);
        const score = document.createElement('strong'); score.textContent = value.toFixed(1);
        row.append(label, meter, score); container.append(row);
    });
}
coverage.addEventListener('input', recalculate);
alternative.addEventListener('change', recalculate);
document.getElementById('reset').addEventListener('click', () => { coverage.value = '3.8'; alternative.checked = false; recalculate(); });
recalculate();
