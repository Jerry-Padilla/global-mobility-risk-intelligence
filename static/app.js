/* Progressive enhancement only: navigation, tables and filters work without JS. */
document.addEventListener('DOMContentLoaded', () => {
    const mode = document.body.dataset.mode;
    const colors = {
        factory: '#167b8d',
        supplier: '#5e77a8',
        earthquake: '#d85d45',
        weather: '#c99b35'
    };
    document.querySelectorAll('[data-map]').forEach(async el => {
        const map = L.map(el, {
            scrollWheelZoom: false,
            minZoom: 0,
            zoomSnap: 0.25,
            maxZoom: 12
        }).setView([27, 10], 2);
        L.control.scale({
            imperial: false
        }).addTo(map);
        map.attributionControl.addAttribution('Natural Earth &middot; public domain | USGS / Open-Meteo where live');
        try {
            const response = await fetch('/static/world.geojson');
            if (!response.ok) throw new Error('Map background unavailable');
            L.geoJSON(await response.json(), {
                style: {
                    color: '#b9cdd6',
                    weight: 1,
                    fillColor: '#f5f8f8',
                    fillOpacity: 1
                },
                interactive: false
            }).addTo(map);
            const points = await fetch(`/api/v1/map/?mode=${mode}`);
            if (!points.ok) throw new Error('Location data unavailable');
            const locations = L.geoJSON(await points.json(), {
                pointToLayer: (f, latlng) => L.circleMarker(latlng, {
                    radius: f.properties.kind === 'factory' ? 6 : 4.5,
                    color: '#fff',
                    weight: 1.5,
                    fillColor: colors[f.properties.kind],
                    fillOpacity: .95
                }),
                onEachFeature: (f, l) => {
                    const box = document.createElement('div');
                    const a = document.createElement('a');
                    a.textContent = f.properties.name;
                    a.href = f.properties.url;
                    box.append(a);
                    l.bindPopup(box);
                }
            }).addTo(map);
            const latitude = Number(el.dataset.latitude);
            const longitude = Number(el.dataset.longitude);
            if (el.dataset.latitude && el.dataset.longitude && Number.isFinite(latitude) && Number.isFinite(longitude)) {
                map.setView([latitude, longitude], 6);
            } else if (locations.getBounds().isValid()) {
                map.fitBounds(locations.getBounds(), {
                    padding: [25, 25],
                    maxZoom: 4
                });
            } else {
                map.fitBounds([
                    [-45, -150],
                    [65, 150]
                ], {
                    padding: [10, 10]
                });
            }
        } catch (error) {
            const note = document.createElement('p');
            note.className = 'notice-error';
            note.textContent = error.message;
            el.after(note);
        }
    });
    const layout = {
        margin: {
            l: 45,
            r: 20,
            t: 24,
            b: 42
        },
        font: {
            family: 'Segoe UI, sans-serif',
            size: 10,
            color: '#67798b'
        },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        xaxis: {
            gridcolor: '#edf1f4'
        },
        yaxis: {
            gridcolor: '#edf1f4'
        },
        showlegend: false
    };

    function plot(id, traces, extra = {}) {
        if (document.getElementById(id)) Plotly.newPlot(id, traces, {
            ...layout,
            ...extra
        }, {
            responsive: true,
            displayModeBar: false
        });
    }
    const history = document.getElementById('risk-history-data');
    if (history) {
        const d = JSON.parse(history.textContent);
        plot('risk-history', [{
            x: d.x,
            y: d.y,
            type: 'scatter',
            mode: 'lines',
            line: {
                color: '#087f8c',
                width: 2
            },
            fill: 'tozeroy',
            fillcolor: 'rgba(8,127,140,.07)'
        }], {
            yaxis: {
                range: [0, 100],
                gridcolor: '#edf1f4'
            }
        });
    }
    const auto = document.getElementById('automotive-data');
    if (auto) {
        const d = JSON.parse(auto.textContent);
        const currentMonth = new Date().toISOString().slice(0, 7);
        plot('complaint-timeline', [{
            x: d.timeline.map(r => r.month),
            y: d.timeline.map(r => r.count),
            type: 'bar',
            customdata: d.timeline.map(r => r.month.slice(0, 7) === currentMonth ? 'Partial month' : 'Completed month'),
            hovertemplate: '%{x|%b %Y}: %{y} complaints<br>%{customdata}<extra></extra>',
            marker: {
                color: d.timeline.map(r => r.month.slice(0, 7) === currentMonth ? '#9aaab6' : '#167b8d')
            }
        }]);
        let runningCount = 0;
        const totalComplaints = d.total_complaints || d.components.reduce((sum, row) => sum + row.count, 0);
        const cumulative = d.components.map(row => {
            runningCount += row.count;
            return totalComplaints ? runningCount / totalComplaints * 100 : 0;
        });
        plot('component-chart', [{
            x: d.components.map(r => r.component),
            y: d.components.map(r => r.count),
            type: 'bar',
            marker: {
                color: '#5e77a8'
            }
        }, {
            x: d.components.map(r => r.component),
            y: cumulative,
            type: 'scatter',
            mode: 'lines+markers',
            yaxis: 'y2',
            line: {color: '#c99b35'},
            hovertemplate: '%{x}<br>%{y:.1f}% cumulative share<extra></extra>'
        }], {
            margin: {l: 45, r: 45, t: 24, b: 65},
            yaxis2: {overlaying: 'y', side: 'right', range: [0, 105], ticksuffix: '%', showgrid: false}
        });
        plot('year-chart', [{
            x: d.years.map(r => String(r.vehicle__year)),
            y: d.years.map(r => r.count),
            type: 'bar',
            marker: {
                color: '#167b8d'
            }
        }], {
            xaxis: {
                type: 'category'
            }
        });
        plot('recall-chart', [{
            x: d.recalls.map(r => r.month),
            y: d.recalls.map(r => r.count),
            type: 'bar',
            marker: {
                color: '#c99b35'
            }
        }]);
    }
});
document.addEventListener('htmx:responseError', event => {
    const n = document.createElement('p');
    n.className = 'notice-error';
    n.textContent = 'The request failed. Please retry.';
    event.detail.target.prepend(n);
});

// Dependent vehicle choices; the GET form remains usable without JavaScript.
document.addEventListener('DOMContentLoaded', () => {
    const data = document.getElementById('vehicle-options');
    if (!data) return;
    const vehicles = JSON.parse(data.textContent);
    const make = document.querySelector('select[name="make"]');
    const model = document.querySelector('select[name="model"]');
    const year = document.querySelector('select[name="year"]');
    function populate(select, values, label) {
        const selected = select.value;
        select.replaceChildren(new Option(label, ''));
        values.forEach(value => select.add(new Option(value, value)));
        select.value = values.includes(selected) ? selected : '';
    }
    function updateYears() {
        const rows = vehicles.filter(v => (!make.value || v.make === make.value) && (!model.value || v.model === model.value));
        populate(year, [...new Set(rows.map(v => String(v.year)))].sort().reverse(), 'All years');
    }
    make.addEventListener('change', () => {
        const rows = vehicles.filter(v => !make.value || v.make === make.value);
        populate(model, [...new Set(rows.map(v => v.model))].sort(), 'All models');
        updateYears();
    });
    model.addEventListener('change', updateYears);
});
