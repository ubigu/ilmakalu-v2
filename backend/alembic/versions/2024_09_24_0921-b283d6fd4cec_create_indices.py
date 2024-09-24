"""Create indices

Revision ID: b283d6fd4cec
Revises: e93c587d5c8f
Create Date: 2024-09-24 09:21:44.845226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b283d6fd4cec'
down_revision: Union[str, None] = 'e93c587d5c8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('build_demolish_index', 'build_demolish_energy_gco2m2', ['scenario', 'year'], unique=False, schema='built')
    op.create_index('build_materia_index', 'build_materia_gco2m2', ['scenario', 'year'], unique=False, schema='built')
    op.create_index('construction_index', 'build_new_construction_energy_gco2m2', ['scenario', 'year'], unique=False, schema='built')
    op.create_index('build_rebuilding_energy_index', 'build_rebuilding_energy_gco2m2', ['scenario', 'year'], unique=False, schema='built')
    op.create_index('build_rebuilding_share_index', 'build_rebuilding_share', ['scenario', 'year', 'rakv'], unique=False, schema='built')
    op.create_index('build_renovation_energy_index', 'build_renovation_energy_gco2m2', ['scenario', 'year'], unique=False, schema='built')
    op.create_index('cooling_proportions_index', 'cooling_proportions_kwhm2', ['scenario', 'rakv'], unique=False, schema='built')
    op.create_index('distribution_heating_system_index', 'distribution_heating_systems', ['scenario', 'year', 'rakv', 'rakennus_tyyppi'], unique=False, schema='built')
    op.create_index('electricity_home_device_index', 'electricity_home_device', ['scenario', 'year'], unique=False, schema='built')
    op.create_index('electricity_home_light_index', 'electricity_home_light', ['scenario', 'year'], unique=False, schema='built')
    op.create_index('electricity_industry_index', 'electricity_iwhs_kwhm2', ['scenario', 'year'], unique=False, schema='built')
    op.create_index('electricity_property_change_index', 'electricity_property_change', ['scenario', 'year'], unique=False, schema='built')
    op.create_index('electricity_property_kwhkm_index', 'electricity_property_kwhm2', ['scenario', 'rakv'], unique=False, schema='built')
    op.create_index('occupancy_index', 'occupancy', ['mun', 'year'], unique=False, schema='built')
    op.create_index('spaces_efficiency_index', 'spaces_efficiency', ['scenario', 'rakv', 'rakennus_tyyppi'], unique=False, schema='built')
    op.create_index('spaces_kwhm2_index', 'spaces_kwhm2', ['scenario', 'rakv', 'year'], unique=False, schema='built')
    op.create_index('water_kwhm2_index', 'water_kwhm2', ['scenario', 'rakv', 'rakennus_tyyppi'], unique=False, schema='built')
    op.create_index('cooling_gco2kwh_index', 'cooling_gco2kwh', ['scenario', 'year'], unique=False, schema='energy')
    op.create_index('district_heating_index', 'district_heating', ['scenario', 'mun', 'year'], unique=False, schema='energy')
    op.create_index('electricity_index', 'electricity', ['scenario', 'year'], unique=False, schema='energy')
    op.create_index('electricity_home_percapita_index', 'electricity_home_percapita', ['mun', 'scenario', 'year'], unique=False, schema='energy')
    op.create_index('heat_source_change_index', 'heat_source_change', ['scenario', 'rakennus_tyyppi'], unique=False, schema='energy')
    op.create_index('heating_degree_days_index', 'heating_degree_days', ['mun'], unique=False, schema='energy')
    op.create_index('spaces_gco2kwh_index', 'spaces_gco2kwh', ['vuosi'], unique=False, schema='energy')
    op.create_index('personal_traffic_index', 'citizen_traffic_stress', ['mun', 'scenario', 'year'], unique=False, schema='traffic')
    op.create_index('industry_performance_index', 'industr_performance', ['scenario', 'year', 'kmuoto'], unique=False, schema='traffic')
    op.create_index('industry_performance_km_index', 'industr_transport_km', ['scenario', 'year', 'kmuoto'], unique=False, schema='traffic')
    op.create_index('mode_power_distribution_index', 'mode_power_distribution', ['scenario', 'year', 'kmuoto'], unique=False, schema='traffic')
    op.create_index('power_fossil_share_index', 'power_fossil_share', ['scenario', 'year'], unique=False, schema='traffic')
    op.create_index('power_kwhkm_index', 'power_kwhkm', ['scenario', 'year', 'kmuoto'], unique=False, schema='traffic')
    op.create_index('service_performance_index', 'service_performance', ['scenario', 'year', 'kmuoto'], unique=False, schema='traffic')
    op.create_index('service_transport_index', 'services_transport_km', ['scenario', 'year', 'kmuoto'], unique=False, schema='traffic')
    op.create_index('workers_traffic_stress_index', 'workers_traffic_stress', ['mun', 'scenario', 'year'], unique=False, schema='traffic')


def downgrade() -> None:
    op.drop_index('workers_traffic_stress_index', table_name='workers_traffic_stress', schema='traffic')
    op.drop_index('service_transport_index', table_name='services_transport_km', schema='traffic')
    op.drop_index('service_performance_index', table_name='service_performance', schema='traffic')
    op.drop_index('power_kwhkm_index', table_name='power_kwhkm', schema='traffic')
    op.drop_index('power_fossil_share_index', table_name='power_fossil_share', schema='traffic')
    op.drop_index('mode_power_distribution_index', table_name='mode_power_distribution', schema='traffic')
    op.drop_index('industry_performance_km_index', table_name='industr_transport_km', schema='traffic')
    op.drop_index('industry_performance_index', table_name='industr_performance', schema='traffic')
    op.drop_index('personal_traffic_index', table_name='citizen_traffic_stress', schema='traffic')
    op.drop_index('spaces_gco2kwh_index', table_name='spaces_gco2kwh', schema='energy')
    op.drop_index('heating_degree_days_index', table_name='heating_degree_days', schema='energy')
    op.drop_index('heat_source_change_index', table_name='heat_source_change', schema='energy')
    op.drop_index('electricity_home_percapita_index', table_name='electricity_home_percapita', schema='energy')
    op.drop_index('electricity_index', table_name='electricity', schema='energy')
    op.drop_index('district_heating_index', table_name='district_heating', schema='energy')
    op.drop_index('cooling_gco2kwh_index', table_name='cooling_gco2kwh', schema='energy')
    op.drop_index('water_kwhm2_index', table_name='water_kwhm2', schema='built')
    op.drop_index('spaces_kwhm2_index', table_name='spaces_kwhm2', schema='built')
    op.drop_index('spaces_efficiency_index', table_name='spaces_efficiency', schema='built')
    op.drop_index('occupancy_index', table_name='occupancy', schema='built')
    op.drop_index('electricity_property_kwhkm_index', table_name='electricity_property_kwhm2', schema='built')
    op.drop_index('electricity_property_change_index', table_name='electricity_property_change', schema='built')
    op.drop_index('electricity_industry_index', table_name='electricity_iwhs_kwhm2', schema='built')
    op.drop_index('electricity_home_light_index', table_name='electricity_home_light', schema='built')
    op.drop_index('electricity_home_device_index', table_name='electricity_home_device', schema='built')
    op.drop_index('distribution_heating_system_index', table_name='distribution_heating_systems', schema='built')
    op.drop_index('cooling_proportions_index', table_name='cooling_proportions_kwhm2', schema='built')
    op.drop_index('build_renovation_energy_index', table_name='build_renovation_energy_gco2m2', schema='built')
    op.drop_index('build_rebuilding_share_index', table_name='build_rebuilding_share', schema='built')
    op.drop_index('build_rebuilding_energy_index', table_name='build_rebuilding_energy_gco2m2', schema='built')
    op.drop_index('construction_index', table_name='build_new_construction_energy_gco2m2', schema='built')
    op.drop_index('build_materia_index', table_name='build_materia_gco2m2', schema='built')
    op.drop_index('build_demolish_index', table_name='build_demolish_energy_gco2m2', schema='built')
