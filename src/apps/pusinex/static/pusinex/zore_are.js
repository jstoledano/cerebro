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

  function pintar(map, destino, datos, tipo, actualAreId = null) {
    destino.clearLayers();
    const geo = L.geoJSON(datos.geojson, {
      style: feature => {
        const p = feature.properties;
        const area = p.ares && p.ares.length ? p.ares[0].numero : 1;
        const actual = actualAreId !== null && (p.ares || []).some(a => Number(a.id) === Number(actualAreId));
        return {
          color: actual ? "#332832" : (tipo === "zore" ? "#454248" : "#57545A"),
          weight: actual ? 4 : (tipo === "zore" ? 2.5 : 1.5),
          opacity: 1,
          fillOpacity: actual ? 0.82 : (tipo === "zore" ? 0.46 : 0.63),
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
      ["Secciones compartidas", z.compartidas],
      ["Municipios comprendidos", (z.municipios || []).length],
      ["Distritos locales comprendidos", (z.distritos_locales || []).length]
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

  }

  function mount(config) {
    const {map, overlays, endpoint, nivel, pk, tab, card, autoEnable, autoFocus, resumenId, statsId} = config;
    const z = L.layerGroup();
    const a = L.layerGroup();
    overlays["ZORE"] = z;
    overlays["ARE"] = a;
    let solicitud;
    let solicitudZore;
    let datosActuales;
    const urlPara = (tipo, identificador) => endpoint + "?nivel=" +
      encodeURIComponent(tipo) + "&pk=" + encodeURIComponent(identificador);
    const pedir = url => fetch(url, {credentials: "same-origin"}).then(response => {
      if (!response.ok) throw new Error("Error consultando ZORE/ARE");
      return response.json();
    });
    const cargar = () => {
      if (!solicitud) solicitud = pedir(urlPara(nivel, pk)).then(datos => {
        datosActuales = datos;
        return datos;
      }).catch(error => { solicitud = undefined; throw error; });
      return solicitud;
    };
    // La vista de una ARE debe consultar TODA la ZORE para su capa contextual.
    // La propia ARE sigue disponible como una capa independiente y resaltada.
    const cargarZore = () => {
      if (nivel !== "are") return cargar();
      if (!solicitudZore) solicitudZore = cargar().then(datos => {
        const grupo = datos.zores[0];
        return grupo ? pedir(urlPara("zore", grupo.id)) : datos;
      }).catch(error => { solicitudZore = undefined; throw error; });
      return solicitudZore;
    };
    const enfocar = geojson => {
      const referencia = L.geoJSON(geojson);
      if (referencia.getLayers().length && referencia.getBounds().isValid()) {
        map.fitBounds(referencia.getBounds(), {padding: [15, 15]});
      }
    };
    const pintarZore = datos => {
      if (!map.hasLayer(z)) return;
      // Todas las secciones y ARE de la ZORE, con un borde destacado para la ARE actual.
      pintar(map, z, datos, nivel === "are" ? "are" : "zore", nivel === "are" ? pk : null);
      if (map.hasLayer(a)) a.eachLayer(group => group.eachLayer(layer => { if (layer.bringToFront) layer.bringToFront(); }));
    };
    const pintarAre = datos => {
      if (!map.hasLayer(a)) return;
      pintar(map, a, datos, "are", nivel === "are" ? pk : null);
    };
    map.on("overlayadd", event => {
      if (event.layer === z) {
        cargarZore().then(datos => {
          pintarZore(datos);
          // La casilla ZORE permite explorar toda su extensión.
          if (nivel === "are" && map.hasLayer(z)) enfocar(datos.geojson);
        }).catch(error => console.error(error));
      }
      if (event.layer === a) {
        cargar().then(datos => {
          pintarAre(datos);
          if (map.hasLayer(z)) a.eachLayer(group => group.eachLayer(layer => { if (layer.bringToFront) layer.bringToFront(); }));
        }).catch(error => console.error(error));
      }
    });
    map.on("overlayremove", event => {
      if (event.layer === z) {
        z.clearLayers();
        if (nivel === "are" && datosActuales) enfocar(datosActuales.geojson);
      }
      if (event.layer === a) a.clearLayers();
    });
    if (tab) instalarPestana(cargar);
    if (card) {
      const div = document.getElementById(card);
      if (div) cargar().then(datos => fichaSeccion(div, datos)).catch(() => {
        div.textContent = "No fue posible cargar la ficha ZORE/ARE.";
      });
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
    if (autoFocus || autoEnable) cargar().then(datos => {
      if (autoFocus && !map.hasLayer(z)) enfocar(datos.geojson);
      if (map.hasLayer(a)) pintarAre(datos);
      if (map.hasLayer(z)) cargarZore().then(pintarZore);
    }).catch(error => console.error(error));
    return {cargar, zoreLayer: z, areLayer: a};
  }

  // Componentes complementarios: cobertura y vecindad geoespacial.
  function mostrarCobertura(elemento, datos) {
    if (!elemento) return;
    elemento.innerHTML = "";
    const z = datos.zores[0];
    if (!z) { elemento.textContent = "Sin cobertura cargada."; return; }
    [["Municipios comprendidos", z.municipios || [], item =>
        String(item.numero).padStart(3, "0") + " · " + item.nombre],
     ["Distritos locales comprendidos", z.distritos_locales || [], item =>
        "Distrito local " + numero(item.numero)]].forEach(([titulo, items, etiqueta]) => {
      const h = document.createElement("h3"); h.className = "font-semibold mt-4 mb-2";
      h.textContent = titulo + " (" + items.length + ")";
      elemento.append(h);
      const tabla = document.createElement("div"); tabla.className = "flex flex-wrap gap-2";
      items.forEach(item => {
        const ficha = document.createElement("span");
        ficha.className = "inline-flex items-center gap-2 border border-base-300 rounded-lg p-2 text-sm";
        ficha.append(enlace(item.url, etiqueta(item)), " · " + formato(item.secciones) + " secciones");
        tabla.append(ficha);
      });
      elemento.append(tabla);
    });
  }

  function montarComplementos(config) {
    const {map, endpoint, nivel, pk, coberturaId, colindanciasId} = config;
    const coverage = coberturaId && document.getElementById(coberturaId);
    if (coverage) {
      fetch(endpoint + "?nivel=" + encodeURIComponent(nivel) + "&pk=" + encodeURIComponent(pk),
        {credentials:"same-origin"}).then(r => {if (!r.ok) throw Error();return r.json();})
        .then(datos => mostrarCobertura(coverage, datos))
        .catch(() => {coverage.textContent = "Cobertura temporalmente no disponible.";});
    }
    const target = colindanciasId && document.getElementById(colindanciasId);
    if (!target) return;
    const layer = L.geoJSON(null, {
      style: {color: "#B46C39", weight: 2.5, fillColor:"#E0AA75", fillOpacity:0.3},
      onEachFeature: (feature, polygon) => {
        const v = feature.properties;
        const pop = document.createElement("div");
        pop.append(enlace(v.url, "Sección " + String(v.numero).padStart(4,"0")));
        polygon.bindPopup(pop);
      }
    });
    const overlays = config.overlays;
    overlays["Secciones colindantes"] = layer;
    // El layer control se construye despues de invocar este método.
    fetch(config.colindanciasEndpoint + "?nivel=" + encodeURIComponent(nivel) + "&pk=" + encodeURIComponent(pk),
      {credentials:"same-origin"}).then(r => {if (!r.ok) throw Error();return r.json();})
      .then(datos => {
        target.innerHTML = "";
        const b = document.createElement("button"); b.type = "button";
        b.className = "btn btn-sm btn-outline mb-4"; b.textContent = "Mostrar / ocultar secciones colindantes";
        b.addEventListener("click", () => map.hasLayer(layer) ? map.removeLayer(layer) : layer.addTo(map));
        target.append(b);
        const lista = document.createElement("div"); lista.className = "grid gap-2";
        datos.vecinas.forEach(v => {
          const item = document.createElement("div"); item.className = "border-b border-base-200 py-2 text-sm";
          const titulo = document.createElement("div");
          titulo.append(enlace(v.url, "Sección " + String(v.numero).padStart(4,"0")));
          item.append(titulo);
          const geo = document.createElement("div");
          geo.className = "flex flex-wrap gap-x-3 gap-y-1 mt-1";
          const clave = (valor, ancho) =>
            valor === null || valor === undefined || valor === ""
              ? "—" : String(valor).padStart(ancho, "0");
          const demarcacion = (url, etiqueta) => {
            if (!url || etiqueta.includes("—")) {
              const span = document.createElement("span");
              span.textContent = etiqueta;
              return span;
            }
            return enlace(url, etiqueta);
          };
          geo.append(
            demarcacion(v.distrito_url, "Distrito federal " + clave(v.distrito, 2)),
            demarcacion(v.distrito_local_url, "Distrito local " + clave(v.distrito_local, 2)),
            demarcacion(v.municipio_url, "Municipio " + clave(v.municipio_numero, 3) + " · " + (v.municipio || "Sin nombre"))
          );
          item.append(geo);
          const info = document.createElement("p"); info.className = "text-xs opacity-75 mt-1";
          if (v.zores.length) {
            info.append("ZORE ");
            v.zores.forEach((z,i) => { if (i) info.append(" / "); info.append(enlace(z.url, "D" + numero(z.distrito) + " Z" + numero(z.numero))); });
          } else info.append("Sin ZORE cargada");
          info.append(" · ");
          if (v.ares.length) {
            v.ares.forEach((a,i) => { if (i) info.append(" / "); info.append(enlace(a.url, "ARE " + numero(a.numero))); });
          } else info.append("Sin ARE cargada");
          item.append(info);
          lista.append(item);
        });
        target.append(lista);
        if (nivel === "zore" && datos.zores_colindantes.length) {
          const footer = document.createElement("p"); footer.className = "text-sm mt-4";
          footer.append("ZORE vecinas · ");
          datos.zores_colindantes.forEach((z, i) => {
            if(i) footer.append(" · ");
            footer.append(enlace(z.url, "D" + numero(z.distrito) + "/Z" + numero(z.numero)));
          });
          target.append(footer);
        }
        layer.addData(datos.geojson);
      }).catch(() => {target.textContent = "No fue posible calcular las colindancias.";});
  }

  window.PusinexZoreAre = {mount, montarComplementos};
})();
