(() => {
  const config = window.DEM_CONFIG;
  if (!config) {
    console.error('Missing DEM_CONFIG — make sure config.js loads before js/app.js');
    return;
  }

  maplibregl.addProtocol('cog', MaplibreCOGProtocol.cogProtocol);

  const map = new maplibregl.Map({
    container: 'map',
    style: 'https://demotiles.maplibre.org/style.json',
    center: config.center,
    zoom: config.zoom,
  });

  map.addControl(new maplibregl.NavigationControl(), 'top-right');

  function cogUrlFor(layer) {
    const ramp = `${layer.colorRamp},${layer.min},${layer.max},c${layer.reverse ? '-' : ''}`;
    return `cog://${config.cogBaseUrl}/${layer.file}#color:${ramp}`;
  }

  let activeId = config.layers[0].id;

  function setActiveLayer(id) {
    activeId = id;
    config.layers.forEach((layer) => {
      if (map.getLayer(layer.id)) {
        map.setLayoutProperty(layer.id, 'visibility', layer.id === id ? 'visible' : 'none');
      }
    });
    const opacitySlider = document.getElementById('opacity-slider');
    opacitySlider.value = 100;
    renderLegend(config.layers.find((layer) => layer.id === id));
  }

  function renderLegend(layer) {
    const gradientEl = document.querySelector('#legend .legend-gradient');
    const titleEl = document.querySelector('#legend .legend-title');
    const minEl = document.querySelector('#legend .legend-min');
    const maxEl = document.querySelector('#legend .legend-max');

    titleEl.textContent = layer.label;
    minEl.textContent = layer.min;
    maxEl.textContent = layer.max;

    try {
      const interpolate = MaplibreCOGProtocol.colorScale({
        colorScheme: layer.colorRamp,
        min: layer.min,
        max: layer.max,
        isContinuous: true,
        isReverse: !!layer.reverse,
      });
      const stops = 10;
      const colors = [];
      for (let i = 0; i <= stops; i += 1) {
        const value = layer.min + ((layer.max - layer.min) * i) / stops;
        const [r, g, b] = interpolate(value);
        colors.push(`rgb(${r},${g},${b})`);
      }
      gradientEl.style.background = `linear-gradient(to right, ${colors.join(',')})`;
    } catch (err) {
      // Older/newer library versions may not expose colorScale on the global —
      // legend still shows title + min/max, just without the gradient swatch.
      console.warn('Could not build legend gradient:', err);
    }
  }

  function buildPanel() {
    const optionsEl = document.getElementById('layer-options');
    config.layers.forEach((layer, index) => {
      const label = document.createElement('label');
      label.className = 'layer-option';
      label.innerHTML = `
        <input type="radio" name="layer" value="${layer.id}" ${index === 0 ? 'checked' : ''} />
        <span>${layer.label}</span>
      `;
      label.querySelector('input').addEventListener('change', () => setActiveLayer(layer.id));
      optionsEl.appendChild(label);
    });

    document.getElementById('opacity-slider').addEventListener('input', (event) => {
      const opacity = Number(event.target.value) / 100;
      if (map.getLayer(activeId)) {
        map.setPaintProperty(activeId, 'raster-opacity', opacity);
      }
    });
  }

  map.on('load', () => {
    config.layers.forEach((layer, index) => {
      map.addSource(layer.id, {
        type: 'raster',
        url: cogUrlFor(layer),
        tileSize: 256,
      });
      map.addLayer({
        id: layer.id,
        type: 'raster',
        source: layer.id,
        layout: { visibility: index === 0 ? 'visible' : 'none' },
        paint: { 'raster-opacity': 1 },
      });
    });

    buildPanel();
    setActiveLayer(activeId);
  });
})();
