window.mockExamples = [
  {
    id: 'example-safety',
    title: 'Fishing safety check',
    explanation_text: 'Sea conditions are generally manageable for the next 24 hours, but wind and swell are elevated enough to caution small boats near Ratnagiri. Keep a close watch on local squall bands and avoid far offshore routes until late afternoon.',
    ui_json: {
      title: 'Fishing safety overview',
      components: [
        {
          type: 'risk-card',
          data: { score: 28.5, level: 'LOW' }
        },
        {
          type: 'weather-card',
          data: {
            temperature_c: 27.3,
            windspeed_kmh: 22.6,
            winddirection_deg: 286,
            precipitation_probability: 90
          }
        },
        {
          type: 'ocean-card',
          data: {
            wave_height_m: 1.68,
            wave_direction_deg: 264,
            wave_period_s: 7.0,
            sea_surface_temperature_c: 28.5
          }
        },
        {
          type: 'pfz-card',
          data: {
            zones: [
              { latitude: 16.7, longitude: 73.2, chlorophyll: 2.71, pfz_score: 0.71 }
            ]
          }
        },
        {
          type: 'marine-map',
          data: {
            markers: [
              { latitude: 16.7, longitude: 73.2, label: 'PFZ zone' }
            ],
            lat: 16.99,
            lon: 73.31,
            zoom: 7
          }
        },
        {
          type: 'recommendation-card',
          data: {
            text: 'Keep operations within 8–10 km of the coast, carry a radio check-in, and postpone deep-water trips if the squall line strengthens.'
          }
        },
        {
          type: 'evidence-panel',
          data: {
            source: 'demo-data',
            checks: ['wind model', 'wave model', 'chlorophyll signal', 'recent coastal alert history']
          }
        }
      ]
    }
  },
  {
    id: 'example-cyclone',
    title: 'Cyclone watch',
    explanation_text: 'There is a moderate cyclone risk developing along the eastern Arabian Sea. Coastal responders should keep a watch on the offshore system and prepare local advisories if the track remains on the current path.',
    ui_json: {
      title: 'Cyclone watch overview',
      components: [
        {
          type: 'risk-card',
          data: { score: 76.1, level: 'HIGH' }
        },
        {
          type: 'alert-card',
          data: {
            cyclone_alerts: [
              { event_name: 'Deep Depression', alert_level: 'Orange', latitude: 14.9, longitude: 71.4 }
            ],
            lightning_alerts: [
              { region: 'Offshore Mumbai', lightning_alert: 'moderate' }
            ]
          }
        },
        {
          type: 'marine-map',
          data: {
            markers: [
              { latitude: 14.9, longitude: 71.4, label: 'Cyclone track point' }
            ],
            lat: 15.6,
            lon: 72.2,
            zoom: 6
          }
        },
        {
          type: 'recommendation-card',
          data: {
            text: 'Issue local alert notices, elevate monitoring frequency, and coordinate with port control if sustained winds increase.'
          }
        }
      ]
    }
  },
  {
    id: 'example-researcher',
    title: 'Chlorophyll + SST readout',
    explanation_text: 'Current chlorophyll and sea surface temperature values indicate productive feeding conditions in the shelf waters. This is a favorable signal for pelagic activity and consistent PFZ development.',
    ui_json: {
      title: 'Marine productivity review',
      components: [
        {
          type: 'ocean-card',
          data: {
            wave_height_m: 1.24,
            wave_direction_deg: 243,
            wave_period_s: 8.2,
            sea_surface_temperature_c: 29.4
          }
        },
        {
          type: 'pfz-card',
          data: {
            zones: [
              { latitude: 9.19, longitude: 76.35, chlorophyll: 2.71, pfz_score: 0.71 },
              { latitude: 10.4, longitude: 75.9, chlorophyll: 2.41, pfz_score: 0.66 }
            ]
          }
        },
        {
          type: 'evidence-panel',
          data: {
            source: 'satellite-archive',
            detail: 'Shelf waters showing elevated productivity and stable thermal structure.'
          }
        }
      ]
    }
  }
];
