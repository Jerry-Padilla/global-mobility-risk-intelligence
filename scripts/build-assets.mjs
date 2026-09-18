import { cpSync, mkdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
mkdirSync('static/vendor', {recursive: true});
mkdirSync('static/build', {recursive: true});
cpSync('node_modules/htmx.org/dist/htmx.min.js', 'static/vendor/htmx.min.js');
cpSync('node_modules/leaflet/dist', 'static/vendor/leaflet', {recursive: true});
cpSync('node_modules/plotly.js-dist-min/plotly.min.js', 'static/vendor/plotly.min.js');
execFileSync(process.execPath, ['node_modules/@tailwindcss/cli/dist/index.mjs', '-i', 'assets/app.css', '-o', 'static/build/app.css', '--minify'], {stdio: 'inherit'});
