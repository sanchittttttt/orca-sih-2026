(function () {
  const riskBadgeClass = (level) => {
    const normalized = String(level || '').toUpperCase();
    if (normalized === 'LOW') return 'low';
    if (normalized === 'MODERATE') return 'moderate';
    if (normalized === 'HIGH') return 'high';
    if (normalized === 'EXTREME') return 'extreme';
    return 'moderate';
  };

  function renderRiskCard(data) {
    const level = data && data.level ? data.level : 'MODERATE';
    const score = typeof data.score === 'number' ? data.score : 50;
    return `
      <div class="detail-panel">
        <h4>Risk card</h4>
        <div class="component-grid">
          <div class="metric-box">
            <span class="metric-label">Level</span>
            <span class="metric-value">${level}</span>
          </div>
          <div class="metric-box">
            <span class="metric-label">Score</span>
            <span class="metric-value">${score}</span>
          </div>
        </div>
      </div>
    `;
  }

  function renderWeatherCard(data) {
    return `
      <div class="detail-panel">
        <h4>Weather</h4>
        <div class="component-grid">
          <div class="metric-box"><span class="metric-label">Temperature</span><span class="metric-value">${data.temperature_c}°C</span></div>
          <div class="metric-box"><span class="metric-label">Wind speed</span><span class="metric-value">${data.windspeed_kmh} km/h</span></div>
          <div class="metric-box"><span class="metric-label">Wind direction</span><span class="metric-value">${data.winddirection_deg}°</span></div>
          <div class="metric-box"><span class="metric-label">Precip probability</span><span class="metric-value">${data.precipitation_probability}%</span></div>
        </div>
      </div>
    `;
  }

  function renderOceanCard(data) {
    return `
      <div class="detail-panel">
        <h4>Ocean</h4>
        <div class="component-grid">
          <div class="metric-box"><span class="metric-label">Wave height</span><span class="metric-value">${data.wave_height_m} m</span></div>
          <div class="metric-box"><span class="metric-label">Wave direction</span><span class="metric-value">${data.wave_direction_deg}°</span></div>
          <div class="metric-box"><span class="metric-label">Wave period</span><span class="metric-value">${data.wave_period_s} s</span></div>
          <div class="metric-box"><span class="metric-label">Sea surface temp</span><span class="metric-value">${data.sea_surface_temperature_c}°C</span></div>
        </div>
      </div>
    `;
  }

  function renderPFZCard(data) {
    const zones = Array.isArray(data.zones) ? data.zones : [];
    const list = zones.length
      ? zones.map((zone) => `
          <li>
            Lat ${zone.latitude}, Lon ${zone.longitude} — chlorophyll ${zone.chlorophyll}, PFZ score ${zone.pfz_score}
          </li>
        `).join('')
      : '<li>No PFZ zones in this dataset.</li>';

    return `
      <div class="detail-panel">
        <h4>PFZ</h4>
        <ul class="pfz-list">${list}</ul>
      </div>
    `;
  }

  function renderAlertCard(data) {
    const cycloneAlerts = Array.isArray(data.cyclone_alerts) ? data.cyclone_alerts : [];
    const lightningAlerts = Array.isArray(data.lightning_alerts) ? data.lightning_alerts : [];

    const cycloneList = cycloneAlerts.length
      ? cycloneAlerts.map((alert) => `<li>${alert.event_name} — ${alert.alert_level} (${alert.latitude}, ${alert.longitude})</li>`).join('')
      : '<li>No active cyclone alerts.</li>';

    const lightningList = lightningAlerts.length
      ? lightningAlerts.map((alert) => `<li>${alert.region} — ${alert.lightning_alert}</li>`).join('')
      : '<li>No lightning alerts.</li>';

    return `
      <div class="detail-panel">
        <h4>Alerts</h4>
        <div class="component-grid">
          <div class="metric-box">
            <span class="metric-label">Cyclone alerts</span>
            <ul class="alert-list">${cycloneList}</ul>
          </div>
          <div class="metric-box">
            <span class="metric-label">Lightning alerts</span>
            <ul class="alert-list">${lightningList}</ul>
          </div>
        </div>
      </div>
    `;
  }

  function renderMarineMap(data) {
    const mapId = `marine-map-${Math.random().toString(36).slice(2, 9)}`;
    const markers = Array.isArray(data.markers) ? data.markers : [];
    const safeMarkers = markers.map((marker) => ({
      latitude: Number(marker.latitude),
      longitude: Number(marker.longitude),
      label: marker.label || 'Marker'
    }));

    const content = `
      <div class="detail-panel">
        <h4>Marine map</h4>
        <div class="map-box" id="${mapId}" data-map-id="${mapId}" data-lat="${data.lat || 16.99}" data-lon="${data.lon || 73.31}" data-zoom="${data.zoom || 6}" data-markers='${JSON.stringify(safeMarkers)}'></div>
      </div>
    `;

    setTimeout(() => {
      const container = document.getElementById(mapId);
      if (container && typeof window.initMarineMap === 'function') {
        const lat = Number(container.dataset.lat || 16.99);
        const lon = Number(container.dataset.lon || 73.31);
        const zoom = Number(container.dataset.zoom || 6);
        window.initMarineMap(mapId, lat, lon, zoom, safeMarkers);
      }
    }, 0);

    return content;
  }

  function renderRecommendationCard(data) {
    return `
      <div class="detail-panel">
        <h4>Recommendation</h4>
        <p>${(data.text || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>
      </div>
    `;
  }

  function renderEvidencePanel(data) {
    return `
      <div class="detail-panel">
        <h4>Evidence panel</h4>
        <div class="json-box">${JSON.stringify(data, null, 2)}</div>
      </div>
    `;
  }

  const registry = {
    'risk-card': renderRiskCard,
    'weather-card': renderWeatherCard,
    'ocean-card': renderOceanCard,
    'pfz-card': renderPFZCard,
    'alert-card': renderAlertCard,
    'marine-map': renderMarineMap,
    'recommendation-card': renderRecommendationCard,
    'evidence-panel': renderEvidencePanel
  };

  window.ComponentRegistry = registry;
  window.riskBadgeClass = riskBadgeClass;

  window.initMarineMap = function (mapId, lat, lon, zoom, markers) {
    const target = document.getElementById(mapId);
    if (!target) return;
    if (target._leaflet_id) return;

    const map = L.map(mapId, { zoomControl: true }).setView([lat, lon], zoom);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
      subdomains: 'abcd',
      maxZoom: 19
    }).addTo(map);

    const list = Array.isArray(markers) ? markers : [];
    if (list.length) {
      const markerLayer = L.layerGroup();
      list.forEach((marker) => {
        if (!marker || Number.isNaN(Number(marker.latitude)) || Number.isNaN(Number(marker.longitude))) return;
        const circle = L.circleMarker([Number(marker.latitude), Number(marker.longitude)], {
          radius: 6,
          color: '#6bcb77',
          fillColor: '#6bcb77',
          fillOpacity: 0.8,
          weight: 1
        });
        circle.bindPopup(`<div style="font-family: var(--font-data); font-size: 0.8rem; color:#0a1014;">${marker.label || 'Marker'}</div>`);
        circle.addTo(markerLayer);
      });
      markerLayer.addTo(map);
    }

    setTimeout(() => map.invalidateSize(), 150);
  };
})();
