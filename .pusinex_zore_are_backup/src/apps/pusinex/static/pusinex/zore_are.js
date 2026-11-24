/* Capas informativas ZORE/ARE para los expedientes PUSINEX.
 * Las franjas de secciones compartidas son simbolos convencionales;
 * no definen limites, manzanas ni particiones territoriales.
 */
(function () {
  "use strict";
  const COLORES = [
    "#9DAFBE", "#C0A8C4", "#A9BA9D", "#CFAD98", "#9BC0BD",
    "#B4ABC7", "#D1BE8F", "#99B0A0", "#C3A3A8", "#B2B8D3",
    "#B9B39B", "#C1ADA0", "#A8C3CE", "#B8C09F", "#CCB1C4"
  ];
  const W3 = "http://www.w3.org/2000/svg";
  const formato = value => value == null ? "Pendiente" : Number(value).toLocaleString("es-MX");
  const numero = value => String(value).padStart(2, "0");
  const color = value => COLORES[(Number(value) - 1 + COLORES.length) % COLORES.length];

  function enlace(url, etiqueta) {
    const a = document.createElement("a");
    a.href = url;
    a.textContent = etiqueta;
    a.className = "link link-primary font-semibold no-underline hover:underline";
    return a;
  }

  function franjaSvg(layer, feature) {
    const areas = feature.properties.ares || [];
    if (areas.length !== 2 || !layer._path) return;
    const svg = layer._path.ownerSVGElement;
    if (!svg) return;
    let defs = svg.querySelector("defs");
    if (!defs) {
      defs = document.createElementNS(W3, "defs");
      svg.insertBefore(defs, svg.firstChild);
    }
    const id = "pusinex-are-" + String(feature.properties.distrito) + "-" + String(feature.properties.numero);
    let pattern = svg.querySelector("#" + id);
    if (!pattern) {
      pattern = document.createElementNS(W3, "pattern");
      pattern.id = id;
      pattern.setAttribute("patternUnits", "userSpaceOnUse");
      pattern.setAttribute("width", "14");
      pattern.setAttribute("height", "14");
      pattern.setAttribute("patternTransform", "rotate(45)");
      const uno = document.createElementNS(W3, "rect");
      uno.setAttribute("width", "14");
      uno.setAttribute("height", "14");
      uno.setAttribute("fill", color(areas[0].numero));
      const dos = document.createElementNS(W3, "rect");
      dos.setAttribute("width", "7");
      dos.setAttribute("height", "14");
      dos.setAttribute("fill", color(areas[1].numero));
      pattern.append(uno, dos);
      defs.appendChild(pattern);
    }
    layer._path.style.fill = "url(#" + id + ")";
    layer._path.setAttribute("fill", "url(#" + id + ")");
  }

  function pintar(map, destino, datos, tipo) {
    destino.clearLayers();
    const geo = L.geoJSON(datos.geojson, {
      style: feature => {
        const p = feature.properties;
        const area = p.ares && p.ares.length ? p.ares[0].numero : 1;
        return {
          color: tipo === "zore" ? "#454248" : "#57545A",
          weight: tipo === "zore" ? 2.5 : 1.5,
          opacity: 1,
          fillOpacity: tipo === "zore" ? 0.46 : 0.63,
          fillColor: color(tipo === "zore" ? p.zore.numero : area)
        };
      },
      onEachFeature: (feature, layer) => {
        const p = feature.properties;
        const ares = p.ares.map(a => numero(a.numero)).join(" / ");
        layer.bindTooltip("Sección " + String(p.numero).padStart(4, "0") +
          " · ZORE " + numero(p.zore.numero) + " · ARE " + ares);
        const popup = document.createElement("div");
        const titular = document.createElement("strong");
        titular.textContent = "Sección " + String(p.numero).padStart(4, "0");
        popup.append(titular, document.createElement("br"),
          enlace(p.url, "Ver expediente sección"), document.createElement("br"),
          enlace(p.zore.url, "ZORE " + numero(p.zore.numero)));
        p.ares.forEach(a => {
          popup.append(document.createElement("br"), enlace(a.url, "ARE " + numero(a.numero)));
        });
        layer.bindPopup(popup);
        if (tipo === "are" && p.compartida) {
          layer.on("add", () => franjaSvg(layer, feature));
        }
      }
    });
    destino.addLayer(geo);
  }

  function fichaSeccion(elemento, datos) {
    elemento.innerHTML = "";
    const sec = datos.secciones[0];
    if (!sec) {
      elemento.textContent = "ZORE y ARE · Sin asignación cargada para esta sección.";
      elemento.className = "rounded-box border border-base-300 p-4";
      return;
    }
    elemento.className = "rounded-box border border-base-300 bg-base-100 p-5 mt-5";
    const encabezado = document.createElement("h2");
    encabezado.className = "font-bold text-xl mb-3";
    encabezado.textContent = "Organización electoral · ZORE y ARE";
    elemento.append(encabezado);
    const p = document.createElement("p");
    p.className = "mb-3";
    p.append("ZORE ", enlace(sec.zore.url, numero(sec.zore.numero)), " · ");
    sec.ares.forEach((a, index) => {
      if (index) p.append(" / ");
      p.append("ARE ", enlace(a.url, numero(a.numero)));
    });
    elemento.append(p);
    if (sec.compartida) {
      const info = document.createElement("p");
      info.className = "text-sm text-base-content/70";
      info.textContent = "Sección con dos ARE. Las franjas del mapa son informativas y no delimitan territorio.";
      elemento.append(info);
      const ul = document.createElement("ul");
      ul.className = "text-sm mt-2 list-disc pl-5";
      sec.ares.forEach(a => {
        const li = document.createElement("li");
        li.textContent = "ARE " + numero(a.numero) + " · Casillas LN asignadas: " + formato(a.casillas_ln) +
          " · LN estimada: " + formato(a.ln_estimada);
        ul.append(li);
      });
      elemento.append(ul);
    }
  }

  function vistaResumen(elemento, datos) {
    elemento.innerHTML = "";
    if (!datos.zores.length) {
      elemento.textContent = "No hay asignaciones ZORE/ARE cargadas para este ámbito.";
      return;
    }
    const areas = new Map(datos.ares.map(a => [a.id, a]));
    const intro = document.createElement("p");
    intro.className = "text-sm text-base-content/70 mb-4";
    intro.textContent = datos.zores.length + " ZORE · " + datos.ares.length +
      " ARE · " + datos.secciones.length + " secciones asignadas.";
    elemento.append(intro);
    datos.zores.forEach(z => {
      const details = document.createElement("details");
      details.className = "border-b border-base-300 py-2";
      const summary = document.createElement("summary");
      summary.className = "cursor-pointer font-medium";
      summary.textContent = "Distrito " + numero(z.distrito) + " · ZORE " + numero(z.numero) +
        " · " + z.areas.length + " ARE · " + z.secciones + " secciones";
      details.append(summary);
      const zonaInfo = document.createElement("p");
      zonaInfo.className = "text-sm my-2";
      zonaInfo.append(enlace(z.url, "Abrir expediente ZORE " + numero(z.numero)),
        " · Padrón " + formato(z.padron) + " · LN " + formato(z.lista_nominal));
      details.append(zonaInfo);
      const ul = document.createElement("ul");
      ul.className = "ml-5 list-disc text-sm space-y-1 pb-2";
      z.areas.forEach(id => {
        const a = areas.get(id);
        if (!a) return;
        const li = document.createElement("li");
        const muestraColor = document.createElement("span");
        muestraColor.setAttribute("aria-hidden", "true");
        muestraColor.className = "inline-block w-3 h-3 rounded-sm border border-base-300 mr-2";
        muestraColor.style.backgroundColor = color(a.numero);
        li.append(muestraColor, enlace(a.url, "ARE " + numero(a.numero)), " · " +
          a.secciones + " sección(es)");
        ul.append(li);
      });
      details.append(ul);
      elemento.append(details);
    });
  }

  function instalarPestana(datosLista) {
    const tablist = document.querySelector('[role="tablist"]');
    if (!tablist) return null;
    const parent = tablist.parentElement;
    const panelPrevio = Array.from(parent.children).find(x => x.getAttribute("role") === "tabpanel");
    const tabPrevio = tablist.querySelector('[role="tab"]');
    if (!panelPrevio || !tabPrevio) return null;
    const button = document.createElement("button");
    button.type = "button";
    button.setAttribute("role", "tab");
    button.className = "tab gap-2";
    button.textContent = "ZORE y ARE";
    tablist.append(button);
    const panel = document.createElement("div");
    panel.setAttribute("role", "tabpanel");
    panel.className = "rounded-b-box border border-t-0 border-base-300 bg-base-100 p-6";
    panel.hidden = true;
    panel.style.display = "none";
    panelPrevio.insertAdjacentElement("afterend", panel);
    button.addEventListener("click", () => {
      tabPrevio.classList.remove("tab-active");
      button.classList.add("tab-active");
      panelPrevio.style.display = "none";
      panel.style.display = "block";
      panel.hidden = false;
      datosLista().then(datos => vistaResumen(panel, datos)).catch(() => {
        panel.textContent = "No fue posible consultar las asignaciones.";
      });
    });
    tabPrevio.addEventListener("click", () => {
      tabPrevio.classList.add("tab-active");
      button.classList.remove("tab-active");
      panelPrevio.style.display = "";
      panel.style.display = "none";
      panel.hidden = true;
    });
    tabPrevio.tabIndex = 0;
    return panel;
  }

  function renderStats(elemento, datos) {
    if (!elemento) return;
    elemento.innerHTML = "";
    const z = datos.zores[0];
    const a = datos.ares[0];
    if (!z) {
      elemento.textContent = "Sin asignaciones cargadas.";
      return;
    }
    const cifras = datos.tipo === "are" && a ? [
      ["Secciones asignadas", a.secciones],
      ["Padrón de secciones asociadas", a.padron_secciones],
      ["Lista nominal estimada", a.ln_estimada],
      ["Secciones compartidas", a.compartidas],
      ["Casillas LN asignadas", a.casillas_ln]
    ] : [
      ["Secciones", z.secciones],
      ["ARE", z.areas.length],
      ["Padrón electoral", z.padron],
      ["Lista nominal", z.lista_nominal],
      ["Secciones compartidas", z.compartidas]
    ];
    cifras.forEach(([label, value]) => {
      const p = document.createElement("p");
      p.className = "border-b border-base-200 py-2 flex justify-between gap-3";
      const b = document.createElement("span");
      b.textContent = label;
      const v = document.createElement("strong");
      v.textContent = formato(value);
      p.append(b, v);
      elemento.append(p);
    });
    if (datos.tipo === "are") {
      const nota = document.createElement("p");
      nota.className = "text-xs opacity-70 mt-3";
      nota.textContent = "El padrón suma secciones completas, incluso las compartidas, y puede repetirse entre ARE. La LN se estima asignando hasta 750 electores por casilla en orden ascendente de ARE; las cifras no sustituyen la asignación nominal efectiva.";
      elemento.append(nota);
    }
  }

  function mount(config) {
    const {map, overlays, endpoint, nivel, pk, tab, card, autoEnable, autoFocus, resumenId, statsId} = config;
    const z = L.layerGroup();
    const a = L.layerGroup();
    overlays["ZORE"] = z;
    overlays["ARE"] = a;
    let solicitud;
    const cargar = () => {
      if (!solicitud) {
        const url = endpoint + "?nivel=" + encodeURIComponent(nivel) + "&pk=" + encodeURIComponent(pk);
        solicitud = fetch(url, {credentials: "same-origin"}).then(response => {
          if (!response.ok) throw new Error("Error consultando ZORE/ARE");
          return response.json();
        });
      }
      return solicitud;
    };
    const dibujar = datos => {
      if (map.hasLayer(z)) pintar(map, z, datos, "zore");
      if (map.hasLayer(a)) pintar(map, a, datos, "are");
      if (autoFocus) {
        const referencia = L.geoJSON(datos.geojson);
        if (referencia.getLayers().length && referencia.getBounds().isValid()) {
          map.fitBounds(referencia.getBounds(), {padding: [15, 15]});
        }
      }
    };
    map.on("overlayadd", event => {
      if (event.layer !== z && event.layer !== a) return;
      cargar().then(dibujar).catch(error => console.error(error));
    });
    map.on("overlayremove", event => {
      if (event.layer === z) z.clearLayers();
      if (event.layer === a) a.clearLayers();
    });
    if (tab) instalarPestana(cargar);
    if (card) {
      const div = document.getElementById(card);
      if (div) {
        cargar().then(datos => fichaSeccion(div, datos)).catch(() => {
          div.textContent = "No fue posible cargar la ficha ZORE/ARE.";
        });
      }
    }
    if (resumenId) {
      const div = document.getElementById(resumenId);
      if (div) cargar().then(datos => vistaResumen(div, datos)).catch(() => {
        div.textContent = "No fue posible cargar el listado.";
      });
    }
    if (statsId) {
      const div = document.getElementById(statsId);
      if (div) cargar().then(datos => renderStats(div, datos)).catch(() => {
        div.textContent = "No fue posible consultar las estadísticas.";
      });
    }
    if (autoEnable === "zore") z.addTo(map);
    if (autoEnable === "are") a.addTo(map);
    if (autoFocus || autoEnable) cargar().then(dibujar).catch(error => console.error(error));
    return {cargar, zoreLayer: z, areLayer: a};
  }
  window.PusinexZoreAre = {mount};
})();
