CREATE INDEX IF NOT EXISTS grid_xyind ON delineations.grid (xyind);

-- Schema BUILT
CREATE INDEX IF NOT EXISTS build_demolish_index ON built.build_demolish_energy_gco2m2 (scenario, year);
CREATE INDEX IF NOT EXISTS build_materia_index ON built.build_materia_gco2m2 (scenario, year);
CREATE INDEX IF NOT EXISTS construction_index ON built.build_new_construction_energy_gco2m2 (scenario, year);
CREATE INDEX IF NOT EXISTS build_rebuilding_energy_index ON built.build_rebuilding_energy_gco2m2 (scenario, year);
CREATE INDEX IF NOT EXISTS build_rebuilding_share ON built.build_rebuilding_share (scenario, year, rakv);
CREATE INDEX IF NOT EXISTS build_renovation_energy_index ON built.build_renovation_energy_gco2m2 (scenario, year);
CREATE INDEX IF NOT EXISTS cooling_proportions_index ON built.cooling_proportions_kwhm2 (scenario, rakv);
CREATE INDEX IF NOT EXISTS distribution_heating_system_index ON built.distribution_heating_systems (scenario, year, rakv, rakennus_tyyppi);
CREATE INDEX IF NOT EXISTS electricity_home_device_index ON built.electricity_home_device (scenario, year);
CREATE INDEX IF NOT EXISTS electricity_home_light_index ON built.electricity_home_light (scenario, year);
CREATE INDEX IF NOT EXISTS electricity_industry_index ON built.electricity_iwhs_kwhm2 (mun, scenario, year);
CREATE INDEX IF NOT EXISTS electricity_property_change_index ON built.electricity_property_change (scenario, year);
CREATE INDEX IF NOT EXISTS electricity_property_kwhkm_index ON built.electricity_property_kwhm2 (scenario, rakv);
CREATE INDEX IF NOT EXISTS occupancy_index ON built.occupancy (mun, year);
CREATE INDEX IF NOT EXISTS spaces_efficiency_index ON built.spaces_efficiency (rakv, rakennus_tyyppi);
CREATE INDEX IF NOT EXISTS spaces_kwhm2_index ON built.spaces_kwhm2 (scenario, rakv, year);
CREATE INDEX IF NOT EXISTS water_kwhm2_index ON built.water_kwhm2 (scenario, rakv, rakennus_tyyppi);

-- Schema ENERGY
CREATE INDEX IF NOT EXISTS district_heating_index ON energy.district_heating (scenario, mun, year);
CREATE INDEX IF NOT EXISTS electricity_index ON energy.electricity (scenario, year);
CREATE INDEX IF NOT EXISTS electricity_home_percapita_index ON energy.electricity_home_percapita (mun, scenario, year);
DROP INDEX IF EXISTS heat_source_change_index;
CREATE INDEX IF NOT EXISTS heat_source_change_index ON energy.heat_source_change (scenario, rakennus_tyyppi, lammitysmuoto);
CREATE INDEX IF NOT EXISTS heating_degree_days_index ON energy.heating_degree_days (mun);
CREATE INDEX IF NOT EXISTS spaces_gco2kwh_index ON energy.spaces_gco2kwh (vuosi);

-- Traffic
CREATE INDEX IF NOT EXISTS personal_traffic_index ON traffic.citizen_traffic_stress (mun, scenario, year);
CREATE INDEX IF NOT EXISTS industry_performance_index ON traffic.industr_performance (scenario, year, kmuoto);
CREATE INDEX IF NOT EXISTS industry_performance_km_index ON traffic.industr_transport_km (scenario, year, kmuoto);
CREATE INDEX IF NOT EXISTS mode_power_distribution_index ON traffic.mode_power_distribution (year, scenario, mun, kmuoto);
CREATE INDEX IF NOT EXISTS power_fossil_share_index ON traffic.power_fossil_share (scenario, year);
CREATE INDEX IF NOT EXISTS power_kwhkm_index ON traffic.power_kwhkm (scenario, year, kmuoto);
CREATE INDEX IF NOT EXISTS service_performance_index ON traffic.service_performance (scenario, year, kmuoto);
CREATE INDEX IF NOT EXISTS service_transport_index ON traffic.services_transport_km (scenario, year, kmuoto);
CREATE INDEX IF NOT EXISTS workers_traffic_stress ON traffic.workers_traffic_stress (mun, scenario, year);