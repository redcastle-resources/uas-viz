(() => {
  const config = window.DEM_CONFIG;
  if (!config) {
    console.error('Missing DEM_CONFIG — make sure config.js loads before js/app.js');
    return;
  }

  maplibregl.addProtocol('cog', MaplibreCOGProtocol.cogProtocol);

  const map = new maplibregl.Map({
    container: 'map',
    style: config.basemapStyle,
    center: config.center,
    zoom: config.zoom,
  });

  map.addControl(new maplibregl.NavigationControl(), 'top-right');

  function cogUrlFor(layer) {
    const ramp = `${layer.colorRamp},${layer.min},${layer.max},c${layer.reverse ? '-' : ''}`;
    return `cog://${config.cogBaseUrl}/${layer.file}#color:${ramp}`;
  }

  // Layers sharing a `group` key are collapsed into a single panel entry/checkbox
  // so e.g. the AOI5 + AOI6 pre-treatment hillshades toggle together.
  const groups = [];
  const groupsByKey = new Map();
  config.layers.forEach((layer) => {
    const key = layer.group || layer.id;
    if (!groupsByKey.has(key)) {
      const group = { key, label: layer.groupLabel || layer.label, layers: [] };
      groupsByKey.set(key, group);
      groups.push(group);
    }
    groupsByKey.get(key).layers.push(layer);
  });

  function isGroupVisible(group) {
    return group.layers.some((layer) => {
      return map.getLayer(layer.id) && map.getLayoutProperty(layer.id, 'visibility') === 'visible';
    });
  }

  let activeGroupKey = groups[0].key;

  function setActiveGroup(group, visible) {
    group.layers.forEach((layer) => {
      if (map.getLayer(layer.id)) {
        map.setLayoutProperty(layer.id, 'visibility', visible ? 'visible' : 'none');
      }
    });

    if (visible) {
      activeGroupKey = group.key;
    } else if (activeGroupKey === group.key) {
      activeGroupKey = [...groups].reverse().find(isGroupVisible)?.key;
    }

    const opacitySlider = document.getElementById('opacity-slider');
    const activeGroup = groups.find((g) => g.key === activeGroupKey);
    opacitySlider.disabled = !activeGroup;
    if (activeGroup) {
      opacitySlider.value = 100;
      renderLegend(activeGroup.layers[0]);
    } else {
      document.querySelector('#legend .legend-title').textContent = 'No layers visible';
      document.querySelector('#legend .legend-gradient').style.background = 'none';
      document.querySelector('#legend .legend-min').textContent = '';
      document.querySelector('#legend .legend-max').textContent = '';
    }
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
    groups.forEach((group, index) => {
      const label = document.createElement('label');
      label.className = 'layer-option';
      label.innerHTML = `
        <input type="checkbox" value="${group.key}" ${index === 0 ? 'checked' : ''} />
        <span>${group.label}</span>
      `;
      label.querySelector('input').addEventListener('change', (event) => {
        setActiveGroup(group, event.target.checked);
      });
      optionsEl.appendChild(label);
    });

    document.getElementById('opacity-slider').addEventListener('input', (event) => {
      const opacity = Number(event.target.value) / 100;
      const activeGroup = groups.find((g) => g.key === activeGroupKey);
      if (activeGroup) {
        activeGroup.layers.forEach((layer) => {
          if (map.getLayer(layer.id)) {
            map.setPaintProperty(layer.id, 'raster-opacity', opacity);
          }
        });
      }
    });
  }

  map.on('load', () => {
    config.layers.forEach((layer) => {
      const groupIndex = groups.findIndex((g) => g.key === (layer.group || layer.id));
      map.addSource(layer.id, {
        type: 'raster',
        url: cogUrlFor(layer),
        tileSize: 256,
      });
      map.addLayer({
        id: layer.id,
        type: 'raster',
        source: layer.id,
        layout: { visibility: groupIndex === 0 ? 'visible' : 'none' },
        paint: { 'raster-opacity': 1 },
      });
    });

    buildPanel();
    setActiveGroup(groups[0], true);
  });
})();
