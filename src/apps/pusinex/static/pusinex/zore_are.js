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

  function textoCabecera(datos) {
    if (datos.tipo === "are" && datos.ares[0]) {
      return "ARE " + numero(datos.ares[0].numero);
    }
    if (datos.tipo === "zore" && datos.zores[0]) {
      return "ZORE " + numero(datos.zores[0].numero);
    }
    return "ZORE y ARE";
  }

  function cuadroSeccion(sec) {
    const fila = document.createElement("li");
    fila.className = "flex flex-wrap items-center gap-2 border-b border-base-200 py-2";
    fila.append(enlace(sec.url, "Sección " + String(sec.numero).padStart(4, "0")));
    if (sec.compartida) {
      const compartida = document.createElement("span");
      compartida.className = "badge badge-outline badge-sm";
      compartida.textContent = "Compartida";
      fila.append(compartida);
    }
    const cifras = document.createElement("span");
    cifras.className = "text-xs opacity-70";
    cifras.textContent = "PE " + formato(sec.padron) + " · LN " + formato(sec.lista_nominal);
    fila.append(cifras);
    return fila;
  }

  function tablaCoberturaLocal(elemento, secciones) {
    if (!secciones.length) return;
    const heading = document.createElement("h3");
    heading.className = "text-lg font-semibold mt-6 mb-2";
    heading.textContent = "Secciones y ARE por distrito local";
    elemento.append(heading);
    const envoltura = document.createElement("div");
    envoltura.className = "overflow-x-auto";
    const tabla = document.createElement("table");
    tabla.className = "table table-zebra table-sm w-full";
    const thead = document.createElement("thead");
    const cab = document.createElement("tr");
    ["Distrito local", "Sección", "Padrón", "Lista nominal", "ARE", "Casillas LN"].forEach(t => {
      const th = document.createElement("th"); th.textContent = t; cab.append(th);
    });
    thead.append(cab); tabla.append(thead);
    const tbody = document.createElement("tbody");
    const grupos = new Map();
    secciones.slice().sort((a,b) => a.distrito_local-b.distrito_local || a.numero-b.numero).forEach(sec => {
      const clave = sec.distrito_local;
      if (!grupos.has(clave)) grupos.set(clave, []);
      grupos.get(clave).push(sec);
    });
    for (const [local, grupo] of grupos) {
      let primeraLocal = true;
      const numeroFilas = grupo.reduce((total, sec) => total + Math.max(1, (sec.ares || []).length), 0);
      grupo.forEach(sec => {
        const areas = (sec.ares && sec.ares.length) ? sec.ares : [null];
        areas.forEach((area, indice) => {
          const tr = document.createElement("tr");
          if (primeraLocal) {
            const td = document.createElement("td");
            td.rowSpan = numeroFilas; td.className = "align-top font-semibold whitespace-nowrap";
            const url = sec.distrito_local_url || ("/cartografia/distrito-local/" + local);
            td.append(enlace(url, "DL " + numero(local)));
            tr.append(td); primeraLocal = false;
          }
          if (indice === 0) {
            const td = document.createElement("td");
            td.rowSpan = areas.length; td.className = "align-top whitespace-nowrap";
            td.append(enlace(sec.url, String(sec.numero).padStart(4, "0")));
            if (sec.compartida) {
              const label = document.createElement("div");
              label.className = "badge badge-outline badge-xs mt-1";
              label.textContent = "Compartida"; td.append(label);
            }
            tr.append(td);
            [sec.padron, sec.lista_nominal].forEach(valor => {
              const t = document.createElement("td");
              t.rowSpan = areas.length; t.className = "align-top tabular-nums";
              t.textContent = formato(valor); tr.append(t);
            });
          }
          const celdaArea = document.createElement("td");
          if (area) celdaArea.append(enlace(area.url, "ARE " + numero(area.numero)));
          else celdaArea.textContent = "—";
          tr.append(celdaArea);
          const casillas = document.createElement("td");
          casillas.className = "tabular-nums";
          casillas.textContent = area ? formato(area.casillas_ln) : "—";
          tr.append(casillas);
          tbody.append(tr);
        });
      });
    }
    tabla.append(tbody); envoltura.append(tabla); elemento.append(envoltura);
  }

  function vistaResumen(elemento, datos, contextoZore = null) {
    elemento.innerHTML = "";
    if (!datos.zores.length) {
      elemento.textContent = "Sin asignaciones ZORE/ARE cargadas para este ámbito.";
      return;
    }
    // En el expediente ARE, el listado corresponde a sus propias secciones.
    // La ZORE es el nivel superior y se consulta mediante un acceso destacado.
    if (datos.tipo === "are") {
      const area = datos.ares[0];
      const zona = (contextoZore && contextoZore.zores[0]) || datos.zores[0];
      const gridAre = document.createElement("div");
      gridAre.className = "grid grid-cols-1 lg:grid-cols-2 gap-6";

      const columnaSecciones = document.createElement("section");
      const hSecciones = document.createElement("h3");
      hSecciones.className = "font-bold mb-3";
      hSecciones.textContent = "Secciones asignadas (" + datos.secciones.length + ")";
      columnaSecciones.append(hSecciones);
      const listaSecciones = document.createElement("ul");
      listaSecciones.className = "text-sm";
      datos.secciones.slice().sort((a, b) => a.numero - b.numero)
        .forEach(sec => listaSecciones.append(cuadroSeccion(sec)));
      columnaSecciones.append(listaSecciones);
      tablaCoberturaLocal(columnaSecciones, datos.secciones);

      const columnaZore = document.createElement("section");
      const tituloZore = document.createElement("h3");
      tituloZore.className = "font-bold mb-3";
      tituloZore.textContent = "ZORE de pertenencia";
      columnaZore.append(tituloZore);
      const tarjeta = document.createElement("div");
      tarjeta.className = "rounded-box border border-base-300 bg-base-200/40 p-5 space-y-3";
      if (zona) {
        const distrito = document.createElement("p");
        distrito.className = "text-sm opacity-70";
        distrito.textContent = "Distrito federal " + numero(zona.distrito);
        const identificador = document.createElement("p");
        identificador.className = "font-bold text-3xl";
        identificador.textContent = "ZORE " + numero(zona.numero);
        const cifras = document.createElement("p");
        cifras.className = "text-sm opacity-75";
        cifras.textContent = formato(zona.areas.length) + " ARE · " +
          formato(zona.secciones) + " secciones";
        const acceso = enlace(zona.url, "Abrir expediente ZORE " + numero(zona.numero));
        acceso.className = "btn btn-primary w-full mt-2";
        tarjeta.append(distrito, identificador, cifras, acceso);
      } else {
        tarjeta.textContent = "Sin ZORE asociada.";
      }
      columnaZore.append(tarjeta);
      gridAre.append(columnaSecciones, columnaZore);
      elemento.append(gridAre);
      return;
    }
    const contexto = contextoZore || datos;
    const aresContexto = new Map(contexto.ares.map(a => [a.id, a]));
    const secciones = datos.secciones;
    const zonas = datos.zores;
    const encabezado = document.createElement("p");
    encabezado.className = "font-semibold mb-3";
    encabezado.textContent = datos.tipo === "zore" || datos.tipo === "are"
      ? textoCabecera(datos) + " · " + secciones.length + " secciones"
      : zonas.length + " ZORE · " + datos.ares.length + " ARE · " + secciones.length + " secciones";
    elemento.append(encabezado);

    zonas.forEach(z => {
      const details = document.createElement("details");
      details.className = "border border-base-300 rounded-lg mb-3 px-4 py-3";
      details.open = datos.tipo === "zore" || datos.tipo === "are";
      const summary = document.createElement("summary");
      summary.className = "cursor-pointer font-medium";
      const areaTotal = datos.tipo === "are" && contexto.zores[0]
        ? contexto.zores[0].areas.length : z.areas.length;
      summary.textContent = (datos.tipo === "are" ? textoCabecera(datos) :
        "Distrito " + numero(z.distrito) + " · ZORE " + numero(z.numero)) +
        " · " + areaTotal + " ARE · " + z.secciones + " secciones" +
        " · PE " + formato(z.padron) + " · LN " + formato(z.lista_nominal);
      details.append(summary);
      if (datos.tipo !== "zore" && datos.tipo !== "are") {
        const acceso = document.createElement("p");
        acceso.className = "text-sm mt-2";
        acceso.append(enlace(z.url, "Ver ZORE " + numero(z.numero)));
        details.append(acceso);
      }

      const grid = document.createElement("div");
      grid.className = "grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4";
      const columnaSecciones = document.createElement("section");
      const hS = document.createElement("h3");
      hS.className = "font-bold mb-2";
      hS.textContent = "Secciones (" + secciones.filter(s => s.zore.id === z.id).length + ")";
      columnaSecciones.append(hS);
      const listaSecciones = document.createElement("ul");
      listaSecciones.className = "text-sm";
      secciones.filter(s => s.zore.id === z.id).sort((a,b) => a.numero-b.numero).forEach(sec => {
        listaSecciones.append(cuadroSeccion(sec));
      });
      columnaSecciones.append(listaSecciones);

      const columnaAres = document.createElement("section");
      const hA = document.createElement("h3");
      hA.className = "font-bold mb-2";
      const ids = datos.tipo === "are" && contexto.zores[0]
        ? contexto.zores[0].areas : z.areas;
      hA.textContent = "ARE (" + ids.length + ")";
      columnaAres.append(hA);
      const listaAres = document.createElement("ul");
      listaAres.className = "text-sm";
      ids.forEach(id => {
        const a = aresContexto.get(id);
        if (!a) return;
        const li = document.createElement("li");
        li.className = "flex items-center gap-2 border-b border-base-200 py-2";
        const muestra = document.createElement("span");
        muestra.className = "inline-block w-3 h-3 rounded-sm";
        muestra.style.backgroundColor = color(a.numero);
        li.append(muestra, enlace(a.url, "ARE " + numero(a.numero)));
        const cantidad = document.createElement("span");
        cantidad.className = "text-xs opacity-70";
        cantidad.textContent = a.secciones + " sección(es)";
        li.append(cantidad);
        listaAres.append(li);
      });
      columnaAres.append(listaAres);
      grid.append(columnaSecciones, columnaAres);
      details.append(grid);
      tablaCoberturaLocal(details, secciones.filter(s => s.zore.id === z.id));
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

  function mostrarAlertaMultilocal(datos) {
    const existentes = document.querySelector('[data-zore-alerta-multilocal="1"]');
    if (existentes) existentes.remove();
    const afectadas = datos.alertas_are_multilocal || [];
    if (!afectadas.length) return;
    const contenido = document.querySelector('main section');
    if (!contenido) return;
    const aviso = document.createElement("div");
    aviso.setAttribute("data-zore-alerta-multilocal", "1");
    aviso.setAttribute("role", "status");
    aviso.className = "alert alert-warning flex flex-wrap gap-2 my-5";
    const titulo = document.createElement("strong");
    titulo.textContent = "¡ATENCIÓN! " + afectadas.length +
      (afectadas.length === 1 ? " ARE comprende" : " ARE comprenden") +
      " secciones de distintos distritos locales.";
    aviso.append(titulo);
    const detalles = document.createElement("span");
    detalles.className = "flex flex-wrap gap-2 text-sm";
    afectadas.forEach(a => {
      detalles.append(enlace(a.url, "D" + numero(a.distrito) + " · ARE " + numero(a.numero)),
        " (DL " + a.distritos_locales.map(numero).join(", ") + ") ");
    });
    aviso.append(detalles);
    const primerMapa = contenido.querySelector('#map');
    if (primerMapa) {
      const fila = primerMapa.closest('.grid');
      if (fila && fila.parentNode) fila.parentNode.insertBefore(aviso, fila);
      else contenido.prepend(aviso);
    } else contenido.prepend(aviso);
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
      if (div) cargar().then(async datos => {
        const contexto = nivel === "are" ? await cargarZore() : null;
        vistaResumen(div, datos, contexto);
      }).catch(() => {
        div.textContent = "No fue posible cargar el listado.";
      });
    }
    if (statsId) {
      const div = document.getElementById(statsId);
      if (div) cargar().then(datos => renderStats(div, datos)).catch(() => {
        div.textContent = "No fue posible consultar las estadísticas.";
      });
    }
    cargar().then(mostrarAlertaMultilocal).catch(error => console.error(error));
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
