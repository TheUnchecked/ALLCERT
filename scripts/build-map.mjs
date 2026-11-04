// Genera site/europe.json: percorsi SVG dei Paesi europei per la mappa.
// Dati: Natural Earth (pacchetto npm "world-atlas", dominio pubblico).
//
// Uso (una tantum, non serve per l'aggiornamento periodico):
//   npm install world-atlas@2 topojson-client@3 topojson-simplify@3 d3-geo@3
//   node scripts/build-map.mjs site/europe.json
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { feature } from "topojson-client";
import { presimplify, simplify } from "topojson-simplify";
import { geoConicConformal, geoPath, geoArea } from "d3-geo";

const require = createRequire(import.meta.url);
const out = process.argv[2] || "site/europe.json";
const topo = JSON.parse(readFileSync(require.resolve("world-atlas/countries-50m.json"), "utf8"));

// Codice numerico ISO 3166-1 -> codice a due lettere.
const CODICI = {
  8: "AL", 20: "AD", 40: "AT", 51: "AM", 31: "AZ", 112: "BY", 56: "BE", 70: "BA", 100: "BG", 191: "HR",
  196: "CY", 203: "CZ", 208: "DK", 233: "EE", 246: "FI", 250: "FR", 268: "GE", 276: "DE", 300: "GR",
  348: "HU", 352: "IS", 372: "IE", 380: "IT", 428: "LV", 438: "LI", 440: "LT", 442: "LU", 470: "MT",
  498: "MD", 492: "MC", 499: "ME", 528: "NL", 807: "MK", 578: "NO", 616: "PL", 620: "PT", 642: "RO",
  643: "RU", 688: "RS", 703: "SK", 705: "SI", 724: "ES", 752: "SE", 756: "CH", 792: "TR",
  804: "UA", 826: "GB",
};

const W = 720, H = 640;
// Finestra geografica mostrata: longitudine -25..45, latitudine 34..71.
const finestra = { type: "Polygon", coordinates: [[[-25, 34], [-25, 71], [45, 71], [45, 34], [-25, 34]]] }; // verso orario, come richiede d3
const dentro = ([lon, lat]) => lon > -25 && lon < 45 && lat > 33 && lat < 72;

const semplificata = simplify(presimplify(topo), 0.02);
const paesi = feature(semplificata, semplificata.objects.countries).features;

// Inquadratura: punti estremi dell'area che vogliamo vedere (Islanda, Portogallo, Cipro, Capo Nord, Caucaso).
const estremi = { type: "MultiPoint", coordinates: [[-24, 65], [-10, 37], [-9, 43], [25, 35], [34, 35], [28, 71], [41, 47], [44, 41]] };
const proiezione = () => geoConicConformal().rotate([-15, 0]).parallels([40, 65]).fitExtent([[6, 6], [W - 6, H - 6]], estremi);
const projection = proiezione();
// Proiezione identica ma senza ritaglio: serve solo per misurare aree e centri.
const misura = geoPath(proiezione());
projection.clipExtent([[0, 0], [W, H]]);
const path = geoPath(projection).digits(1);

const risultato = { width: W, height: H, countries: {}, dots: {} };
for (const f of paesi) {
  const code = CODICI[+f.id];
  if (!code) continue;

  // Tieni solo i poligoni dentro la finestra (toglie Guyana, Azzorre, Canarie, Svalbard...).
  let geom = f.geometry;
  if (geom.type === "MultiPolygon") {
    const poligoni = geom.coordinates.filter(p => p[0].some(dentro));
    if (!poligoni.length) continue;
    geom = { type: "MultiPolygon", coordinates: poligoni };
  } else if (!geom.coordinates[0].some(dentro)) continue;

  const d = path({ type: "Feature", geometry: geom });
  if (!d) continue;
  risultato.countries[code] = d;

  // Stati minuscoli: aggiungi un punto cliccabile al centro.
  const areaPx = misura.area({ type: "Feature", geometry: geom });
  if (areaPx < 60) {
    const [x, y] = misura.centroid({ type: "Feature", geometry: geom });
    if (Number.isFinite(x) && x > 10 && x < W - 10 && y > 10 && y < H - 10) risultato.dots[code] = [Math.round(x * 10) / 10, Math.round(y * 10) / 10];
  }
}

writeFileSync(out, JSON.stringify(risultato));
console.log(`${Object.keys(risultato.countries).length} Paesi, ${Object.keys(risultato.dots).length} punti, ${(JSON.stringify(risultato).length / 1024).toFixed(0)} KB -> ${out}`);
