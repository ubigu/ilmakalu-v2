"""Initial migration

Revision ID: fad8f477458f
Revises: 
Create Date: 2024-09-24 14:28:25.934306

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = 'fad8f477458f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA built")
    op.execute("CREATE SCHEMA delineations")
    op.execute("CREATE SCHEMA energy")
    op.execute("CREATE SCHEMA grid_globals")
    op.execute("CREATE SCHEMA traffic")
    op.create_table('build_demolish_energy_gco2m2',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('erpien', sa.Float(), nullable=False),
    sa.Column('rivita', sa.Float(), nullable=False),
    sa.Column('askert', sa.Float(), nullable=False),
    sa.Column('liike', sa.Float(), nullable=False),
    sa.Column('tsto', sa.Float(), nullable=False),
    sa.Column('liiken', sa.Float(), nullable=False),
    sa.Column('hoito', sa.Float(), nullable=False),
    sa.Column('kokoon', sa.Float(), nullable=False),
    sa.Column('opetus', sa.Float(), nullable=False),
    sa.Column('teoll', sa.Float(), nullable=False),
    sa.Column('varast', sa.Float(), nullable=False),
    sa.Column('muut', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year'),
    schema='built'
    )
    op.create_index('build_demolish_index', 'build_demolish_energy_gco2m2', ['scenario', 'year'], unique=False, schema='built')
    op.create_table('build_materia_gco2m2',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('erpien', sa.Float(), nullable=False),
    sa.Column('rivita', sa.Float(), nullable=False),
    sa.Column('askert', sa.Float(), nullable=False),
    sa.Column('liike', sa.Float(), nullable=False),
    sa.Column('tsto', sa.Float(), nullable=False),
    sa.Column('liiken', sa.Float(), nullable=False),
    sa.Column('hoito', sa.Float(), nullable=False),
    sa.Column('kokoon', sa.Float(), nullable=False),
    sa.Column('opetus', sa.Float(), nullable=False),
    sa.Column('teoll', sa.Float(), nullable=False),
    sa.Column('varast', sa.Float(), nullable=False),
    sa.Column('muut', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year'),
    schema='built'
    )
    op.create_index('build_materia_index', 'build_materia_gco2m2', ['scenario', 'year'], unique=False, schema='built')
    op.create_table('build_new_construction_energy_gco2m2',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('erpien', sa.Float(), nullable=False),
    sa.Column('rivita', sa.Float(), nullable=False),
    sa.Column('askert', sa.Float(), nullable=False),
    sa.Column('liike', sa.Float(), nullable=False),
    sa.Column('tsto', sa.Float(), nullable=False),
    sa.Column('liiken', sa.Float(), nullable=False),
    sa.Column('hoito', sa.Float(), nullable=False),
    sa.Column('kokoon', sa.Float(), nullable=False),
    sa.Column('opetus', sa.Float(), nullable=False),
    sa.Column('teoll', sa.Float(), nullable=False),
    sa.Column('varast', sa.Float(), nullable=False),
    sa.Column('muut', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year'),
    schema='built'
    )
    op.create_index('construction_index', 'build_new_construction_energy_gco2m2', ['scenario', 'year'], unique=False, schema='built')
    op.create_table('build_rebuilding_energy_gco2m2',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('erpien', sa.Float(), nullable=False),
    sa.Column('rivita', sa.Float(), nullable=False),
    sa.Column('askert', sa.Float(), nullable=False),
    sa.Column('liike', sa.Float(), nullable=False),
    sa.Column('tsto', sa.Float(), nullable=False),
    sa.Column('liiken', sa.Float(), nullable=False),
    sa.Column('hoito', sa.Float(), nullable=False),
    sa.Column('kokoon', sa.Float(), nullable=False),
    sa.Column('opetus', sa.Float(), nullable=False),
    sa.Column('teoll', sa.Float(), nullable=False),
    sa.Column('varast', sa.Float(), nullable=False),
    sa.Column('muut', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year'),
    schema='built'
    )
    op.create_index('build_rebuilding_energy_index', 'build_rebuilding_energy_gco2m2', ['scenario', 'year'], unique=False, schema='built')
    op.create_table('build_rebuilding_share',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('rakv', sa.Integer(), nullable=False),
    sa.Column('erpien', sa.Float(), nullable=False),
    sa.Column('rivita', sa.Float(), nullable=False),
    sa.Column('askert', sa.Float(), nullable=False),
    sa.Column('liike', sa.Float(), nullable=False),
    sa.Column('tsto', sa.Float(), nullable=False),
    sa.Column('liiken', sa.Float(), nullable=False),
    sa.Column('hoito', sa.Float(), nullable=False),
    sa.Column('kokoon', sa.Float(), nullable=False),
    sa.Column('opetus', sa.Float(), nullable=False),
    sa.Column('teoll', sa.Float(), nullable=False),
    sa.Column('varast', sa.Float(), nullable=False),
    sa.Column('muut', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year', 'rakv'),
    schema='built'
    )
    op.create_index('build_rebuilding_share_index', 'build_rebuilding_share', ['scenario', 'year', 'rakv'], unique=False, schema='built')
    op.create_table('build_renovation_energy_gco2m2',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('erpien', sa.Float(), nullable=False),
    sa.Column('rivita', sa.Float(), nullable=False),
    sa.Column('askert', sa.Float(), nullable=False),
    sa.Column('liike', sa.Float(), nullable=False),
    sa.Column('tsto', sa.Float(), nullable=False),
    sa.Column('liiken', sa.Float(), nullable=False),
    sa.Column('hoito', sa.Float(), nullable=False),
    sa.Column('kokoon', sa.Float(), nullable=False),
    sa.Column('opetus', sa.Float(), nullable=False),
    sa.Column('teoll', sa.Float(), nullable=False),
    sa.Column('varast', sa.Float(), nullable=False),
    sa.Column('muut', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year'),
    schema='built'
    )
    op.create_index('build_renovation_energy_index', 'build_renovation_energy_gco2m2', ['scenario', 'year'], unique=False, schema='built')
    op.create_table('cooling_proportions_kwhm2',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('rakv', sa.Integer(), nullable=False),
    sa.Column('rakennus_tyyppi', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('jaahdytys_osuus', sa.Float(), nullable=False),
    sa.Column('jaahdytys_kwhm2', sa.Float(), nullable=False),
    sa.Column('jaahdytys_kaukok', sa.Float(), nullable=False),
    sa.Column('jaahdytys_sahko', sa.Float(), nullable=False),
    sa.Column('jaahdytys_pumput', sa.Float(), nullable=False),
    sa.Column('jaahdytys_muu', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'rakv', 'rakennus_tyyppi'),
    schema='built'
    )
    op.create_index('cooling_proportions_index', 'cooling_proportions_kwhm2', ['scenario', 'rakv'], unique=False, schema='built')
    op.create_table('distribution_heating_systems',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('rakv', sa.Integer(), nullable=False),
    sa.Column('rakennus_tyyppi', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('kaukolampo', sa.Float(), nullable=False),
    sa.Column('kevyt_oljy', sa.Float(), nullable=False),
    sa.Column('kaasu', sa.Float(), nullable=False),
    sa.Column('sahko', sa.Float(), nullable=False),
    sa.Column('puu', sa.Float(), nullable=False),
    sa.Column('maalampo', sa.Float(), nullable=False),
    sa.Column('muu_lammitys', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year', 'rakv', 'rakennus_tyyppi'),
    schema='built'
    )
    op.create_index('distribution_heating_system_index', 'distribution_heating_systems', ['scenario', 'year', 'rakv', 'rakennus_tyyppi'], unique=False, schema='built')
    op.create_table('electricity_home_device',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('erpien', sa.Float(), nullable=False),
    sa.Column('rivita', sa.Float(), nullable=False),
    sa.Column('askert', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year'),
    schema='built'
    )
    op.create_index('electricity_home_device_index', 'electricity_home_device', ['scenario', 'year'], unique=False, schema='built')
    op.create_table('electricity_home_light',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('erpien', sa.Float(), nullable=False),
    sa.Column('rivita', sa.Float(), nullable=False),
    sa.Column('askert', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year'),
    schema='built'
    )
    op.create_index('electricity_home_light_index', 'electricity_home_light', ['scenario', 'year'], unique=False, schema='built')
    op.create_table('electricity_iwhs_kwhm2',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('myymal_hyper', sa.Float(), nullable=False),
    sa.Column('myymal_super', sa.Float(), nullable=False),
    sa.Column('myymal_pien', sa.Float(), nullable=False),
    sa.Column('myymal_muu', sa.Float(), nullable=False),
    sa.Column('majoit', sa.Float(), nullable=False),
    sa.Column('asla', sa.Float(), nullable=False),
    sa.Column('ravint', sa.Float(), nullable=False),
    sa.Column('tsto', sa.Float(), nullable=False),
    sa.Column('liiken', sa.Float(), nullable=False),
    sa.Column('hoito', sa.Float(), nullable=False),
    sa.Column('kokoon', sa.Float(), nullable=False),
    sa.Column('opetus', sa.Float(), nullable=False),
    sa.Column('muut', sa.Float(), nullable=False),
    sa.Column('teoll_kaivos', sa.Float(), nullable=False),
    sa.Column('teoll_elint', sa.Float(), nullable=False),
    sa.Column('teoll_tekst', sa.Float(), nullable=False),
    sa.Column('teoll_puu', sa.Float(), nullable=False),
    sa.Column('teoll_paper', sa.Float(), nullable=False),
    sa.Column('teoll_kemia', sa.Float(), nullable=False),
    sa.Column('teoll_miner', sa.Float(), nullable=False),
    sa.Column('teoll_mjalos', sa.Float(), nullable=False),
    sa.Column('teoll_metal', sa.Float(), nullable=False),
    sa.Column('teoll_kone', sa.Float(), nullable=False),
    sa.Column('teoll_muu', sa.Float(), nullable=False),
    sa.Column('teoll_energ', sa.Float(), nullable=False),
    sa.Column('teoll_vesi', sa.Float(), nullable=False),
    sa.Column('teoll_yhdysk', sa.Float(), nullable=False),
    sa.Column('varast', sa.Float(), nullable=False),
    sa.Column('teoll', sa.Float(), nullable=False),
    sa.Column('liike', sa.Float(), nullable=False),
    sa.Column('myymal', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year'),
    schema='built'
    )
    op.create_index('electricity_industry_index', 'electricity_iwhs_kwhm2', ['scenario', 'year'], unique=False, schema='built')
    op.create_table('electricity_property_change',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('9999', sa.Float(), nullable=False),
    sa.Column('1920', sa.Float(), nullable=False),
    sa.Column('1929', sa.Float(), nullable=False),
    sa.Column('1939', sa.Float(), nullable=False),
    sa.Column('1949', sa.Float(), nullable=False),
    sa.Column('1959', sa.Float(), nullable=False),
    sa.Column('1969', sa.Float(), nullable=False),
    sa.Column('1979', sa.Float(), nullable=False),
    sa.Column('1989', sa.Float(), nullable=False),
    sa.Column('1999', sa.Float(), nullable=False),
    sa.Column('2009', sa.Float(), nullable=False),
    sa.Column('2010', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year'),
    schema='built'
    )
    op.create_index('electricity_property_change_index', 'electricity_property_change', ['scenario', 'year'], unique=False, schema='built')
    op.create_table('electricity_property_kwhm2',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('rakv', sa.Integer(), nullable=False),
    sa.Column('rakennus_tyyppi', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('sahko_kiinteisto_kwhm2', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'rakv', 'rakennus_tyyppi'),
    schema='built'
    )
    op.create_index('electricity_property_kwhkm_index', 'electricity_property_kwhm2', ['scenario', 'rakv'], unique=False, schema='built')
    op.create_table('iwhs_sizes',
    sa.Column('type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('several', sa.Integer(), nullable=False),
    sa.Column('single', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('type'),
    schema='built'
    )
    op.create_table('occupancy',
    sa.Column('mun', sa.Integer(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('erpien', sa.REAL(), nullable=True),
    sa.Column('rivita', sa.REAL(), nullable=True),
    sa.Column('askert', sa.REAL(), nullable=True),
    sa.PrimaryKeyConstraint('mun', 'year'),
    schema='built'
    )
    op.create_index('occupancy_index', 'occupancy', ['mun', 'year'], unique=False, schema='built')
    op.create_table('spaces_efficiency',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('rakv', sa.Integer(), nullable=False),
    sa.Column('rakennus_tyyppi', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('kaukolampo', sa.Float(), nullable=False),
    sa.Column('kevyt_oljy', sa.Float(), nullable=False),
    sa.Column('raskas_oljy', sa.Float(), nullable=False),
    sa.Column('kaasu', sa.Float(), nullable=False),
    sa.Column('sahko', sa.Float(), nullable=False),
    sa.Column('puu', sa.Float(), nullable=False),
    sa.Column('turve', sa.Float(), nullable=False),
    sa.Column('hiili', sa.Float(), nullable=False),
    sa.Column('maalampo', sa.Float(), nullable=False),
    sa.Column('muu_lammitys', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'rakv', 'rakennus_tyyppi'),
    schema='built'
    )
    op.create_index('spaces_efficiency_index', 'spaces_efficiency', ['scenario', 'rakv', 'rakennus_tyyppi'], unique=False, schema='built')
    op.create_table('spaces_kwhm2',
    sa.Column('mun', sa.Integer(), nullable=False),
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('rakv', sa.Integer(), nullable=False),
    sa.Column('erpien', sa.Float(), nullable=False),
    sa.Column('rivita', sa.Float(), nullable=False),
    sa.Column('askert', sa.Float(), nullable=False),
    sa.Column('liike', sa.Float(), nullable=False),
    sa.Column('tsto', sa.Float(), nullable=False),
    sa.Column('liiken', sa.Float(), nullable=False),
    sa.Column('hoito', sa.Float(), nullable=False),
    sa.Column('kokoon', sa.Float(), nullable=False),
    sa.Column('opetus', sa.Float(), nullable=False),
    sa.Column('teoll', sa.Float(), nullable=False),
    sa.Column('varast', sa.Float(), nullable=False),
    sa.Column('muut', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('mun', 'scenario', 'year', 'rakv'),
    schema='built'
    )
    op.create_index('spaces_kwhm2_index', 'spaces_kwhm2', ['scenario', 'rakv', 'year'], unique=False, schema='built')
    op.create_table('water_kwhm2',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('rakv', sa.Integer(), nullable=False),
    sa.Column('rakennus_tyyppi', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('vesi_kwh_m2', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'rakv', 'rakennus_tyyppi'),
    schema='built'
    )
    op.create_index('water_kwhm2_index', 'water_kwhm2', ['scenario', 'rakv', 'rakennus_tyyppi'], unique=False, schema='built')
    op.create_table('centroids',
    sa.Column('WKT', geoalchemy2.types.Geometry(geometry_type='POINT', from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('keskustyyp', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('keskusnimi', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    schema='delineations'
    )
    op.create_table('grid',
    sa.Column('WKT', geoalchemy2.types.Geometry(geometry_type='MULTIPOLYGON', from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
    sa.Column('xyind', sa.VARCHAR(length=13), nullable=False),
    sa.Column('mun', sa.Integer(), nullable=False),
    sa.Column('zone', sa.BIGINT(), nullable=True),
    sa.Column('centdist', sa.SMALLINT(), nullable=True),
    sa.PrimaryKeyConstraint('xyind'),
    schema='delineations'
    )
    op.create_table('cooling_gco2kwh',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('kaukok', sa.Integer(), nullable=False),
    sa.Column('sahko', sa.Integer(), nullable=False),
    sa.Column('pumput', sa.Integer(), nullable=False),
    sa.Column('muu', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year'),
    schema='energy'
    )
    op.create_index('cooling_gco2kwh_index', 'cooling_gco2kwh', ['scenario', 'year'], unique=False, schema='energy')
    op.create_table('district_heating',
    sa.Column('mun', sa.Integer(), nullable=False),
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('em', sa.Integer(), nullable=False),
    sa.Column('hjm', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('mun', 'scenario', 'year'),
    schema='energy'
    )
    op.create_index('district_heating_index', 'district_heating', ['scenario', 'mun', 'year'], unique=False, schema='energy')
    op.create_table('electricity',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('metodi', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('paastolaji', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('gco2kwh', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year', 'metodi', 'paastolaji'),
    schema='energy'
    )
    op.create_index('electricity_index', 'electricity', ['scenario', 'year'], unique=False, schema='energy')
    op.create_table('electricity_home_percapita',
    sa.Column('mun', sa.Integer(), nullable=False),
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('sahko_koti_as', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('mun', 'scenario', 'year'),
    schema='energy'
    )
    op.create_index('electricity_home_percapita_index', 'electricity_home_percapita', ['mun', 'scenario', 'year'], unique=False, schema='energy')
    op.create_table('heat_source_change',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('rakennus_tyyppi', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('lammitysmuoto', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('kaukolampo', sa.Float(), nullable=False),
    sa.Column('kevyt_oljy', sa.Float(), nullable=False),
    sa.Column('kaasu', sa.Float(), nullable=False),
    sa.Column('sahko', sa.Float(), nullable=False),
    sa.Column('puu', sa.Float(), nullable=False),
    sa.Column('maalampo', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'rakennus_tyyppi', 'lammitysmuoto'),
    schema='energy'
    )
    op.create_index('heat_source_change_index', 'heat_source_change', ['scenario', 'rakennus_tyyppi'], unique=False, schema='energy')
    op.create_table('heating_degree_days',
    sa.Column('mun', sa.Integer(), nullable=False),
    sa.Column('mun_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('degreedays', sa.Integer(), nullable=False),
    sa.Column('multiplier', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('mun'),
    schema='energy'
    )
    op.create_index('heating_degree_days_index', 'heating_degree_days', ['mun'], unique=False, schema='energy')
    op.create_table('spaces_gco2kwh',
    sa.Column('vuosi', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('kaukolampo', sa.Integer(), nullable=False),
    sa.Column('kevyt_oljy', sa.Integer(), nullable=False),
    sa.Column('raskas_oljy', sa.Integer(), nullable=False),
    sa.Column('kaasu', sa.Integer(), nullable=False),
    sa.Column('sahko', sa.Integer(), nullable=False),
    sa.Column('puu', sa.Integer(), nullable=False),
    sa.Column('turve', sa.Integer(), nullable=False),
    sa.Column('hiili', sa.Integer(), nullable=False),
    sa.Column('maalampo', sa.Integer(), nullable=False),
    sa.Column('muu_lammitys', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('vuosi'),
    schema='energy'
    )
    op.create_index('spaces_gco2kwh_index', 'spaces_gco2kwh', ['vuosi'], unique=False, schema='energy')
    op.create_table('buildings',
    sa.Column('xyind', sa.VARCHAR(length=13), nullable=False),
    sa.Column('rakv', sa.Integer(), nullable=False),
    sa.Column('energiam', sa.VARCHAR(), nullable=False),
    sa.Column('rakyht_lkm', sa.Integer(), nullable=False),
    sa.Column('teoll_lkm', sa.Integer(), nullable=False),
    sa.Column('varast_lkm', sa.Integer(), nullable=False),
    sa.Column('rakyht_ala', sa.REAL(), nullable=True),
    sa.Column('asuin_ala', sa.REAL(), nullable=True),
    sa.Column('erpien_ala', sa.REAL(), nullable=True),
    sa.Column('rivita_ala', sa.REAL(), nullable=True),
    sa.Column('askert_ala', sa.REAL(), nullable=True),
    sa.Column('liike_ala', sa.REAL(), nullable=True),
    sa.Column('myymal_ala', sa.REAL(), nullable=True),
    sa.Column('myymal_pien_ala', sa.REAL(), nullable=True),
    sa.Column('myymal_super_ala', sa.REAL(), nullable=True),
    sa.Column('myymal_hyper_ala', sa.REAL(), nullable=True),
    sa.Column('myymal_muu_ala', sa.REAL(), nullable=True),
    sa.Column('majoit_ala', sa.REAL(), nullable=True),
    sa.Column('asla_ala', sa.REAL(), nullable=True),
    sa.Column('ravint_ala', sa.REAL(), nullable=True),
    sa.Column('tsto_ala', sa.REAL(), nullable=True),
    sa.Column('liiken_ala', sa.REAL(), nullable=True),
    sa.Column('hoito_ala', sa.REAL(), nullable=True),
    sa.Column('kokoon_ala', sa.REAL(), nullable=True),
    sa.Column('opetus_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_elint_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_tekst_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_puu_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_paper_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_miner_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_kemia_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_kone_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_mjalos_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_metal_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_vesi_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_energ_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_yhdysk_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_kaivos_ala', sa.REAL(), nullable=True),
    sa.Column('teoll_muu_ala', sa.REAL(), nullable=True),
    sa.Column('varast_ala', sa.REAL(), nullable=True),
    sa.Column('muut_ala', sa.REAL(), nullable=True),
    sa.PrimaryKeyConstraint('xyind', 'rakv', 'energiam'),
    schema='grid_globals'
    )
    op.create_table('clc',
    sa.Column('vuosi', sa.Integer(), nullable=False),
    sa.Column('kunta', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('maa_ha', sa.REAL(), nullable=True),
    sa.Column('vesi_ha', sa.Float(), nullable=False),
    sa.Column('clc1111', sa.Float(), nullable=False),
    sa.Column('clc1121', sa.Float(), nullable=False),
    sa.Column('clc1211', sa.Float(), nullable=False),
    sa.Column('clc1212', sa.Float(), nullable=False),
    sa.Column('clc1221', sa.Float(), nullable=False),
    sa.Column('clc1231', sa.Float(), nullable=False),
    sa.Column('clc1241', sa.Float(), nullable=False),
    sa.Column('clc1311', sa.Float(), nullable=False),
    sa.Column('clc1312', sa.Float(), nullable=False),
    sa.Column('clc1321', sa.Float(), nullable=False),
    sa.Column('clc1331', sa.Float(), nullable=False),
    sa.Column('clc1411', sa.Float(), nullable=False),
    sa.Column('clc1421', sa.Float(), nullable=False),
    sa.Column('clc1422', sa.Float(), nullable=False),
    sa.Column('clc1423', sa.Float(), nullable=False),
    sa.Column('clc1424', sa.Float(), nullable=False),
    sa.Column('clc2111', sa.Float(), nullable=False),
    sa.Column('clc2221', sa.Float(), nullable=False),
    sa.Column('clc2311', sa.Float(), nullable=False),
    sa.Column('clc2312', sa.Float(), nullable=False),
    sa.Column('clc2431', sa.Float(), nullable=False),
    sa.Column('clc2441', sa.Float(), nullable=False),
    sa.Column('clc3111', sa.Float(), nullable=False),
    sa.Column('clc3112', sa.Float(), nullable=False),
    sa.Column('clc3121', sa.Float(), nullable=False),
    sa.Column('clc3122', sa.Float(), nullable=False),
    sa.Column('clc3123', sa.Float(), nullable=False),
    sa.Column('clc3131', sa.Float(), nullable=False),
    sa.Column('clc3132', sa.Float(), nullable=False),
    sa.Column('clc3133', sa.Float(), nullable=False),
    sa.Column('clc3211', sa.Float(), nullable=False),
    sa.Column('clc3221', sa.Float(), nullable=False),
    sa.Column('clc3241', sa.Float(), nullable=False),
    sa.Column('clc3242', sa.Float(), nullable=False),
    sa.Column('clc3243', sa.Float(), nullable=False),
    sa.Column('clc3244', sa.Float(), nullable=False),
    sa.Column('clc3246', sa.Float(), nullable=False),
    sa.Column('clc3311', sa.Float(), nullable=False),
    sa.Column('clc3321', sa.Float(), nullable=False),
    sa.Column('clc3331', sa.Float(), nullable=False),
    sa.Column('clc4111', sa.Float(), nullable=False),
    sa.Column('clc4112', sa.Float(), nullable=False),
    sa.Column('clc4121', sa.Float(), nullable=False),
    sa.Column('clc4122', sa.Float(), nullable=False),
    sa.Column('clc4211', sa.Float(), nullable=False),
    sa.Column('clc4212', sa.Float(), nullable=False),
    sa.Column('clc5111', sa.Float(), nullable=False),
    sa.Column('clc5121', sa.Float(), nullable=False),
    sa.Column('clc5231', sa.Float(), nullable=False),
    sa.Column('xyind', sa.VARCHAR(length=13), nullable=False),
    sa.PrimaryKeyConstraint('vuosi', 'kunta', 'xyind'),
    schema='grid_globals'
    )
    op.create_table('employ',
    sa.Column('vuosi', sa.Integer(), nullable=False),
    sa.Column('kunta', sa.Integer(), nullable=False),
    sa.Column('tp_yht', sa.SMALLINT(), nullable=True),
    sa.Column('xyind', sa.VARCHAR(length=13), nullable=False),
    sa.PrimaryKeyConstraint('vuosi', 'kunta', 'xyind'),
    schema='grid_globals'
    )
    op.create_table('pop',
    sa.Column('vuosi', sa.Integer(), nullable=False),
    sa.Column('kunta', sa.Integer(), nullable=False),
    sa.Column('xyind', sa.VARCHAR(length=13), nullable=False),
    sa.Column('v_yht', sa.SMALLINT(), nullable=True),
    sa.Column('v_0_6', sa.SMALLINT(), nullable=True),
    sa.Column('v_7_14', sa.SMALLINT(), nullable=True),
    sa.Column('v_15_17', sa.SMALLINT(), nullable=True),
    sa.Column('v_18_29', sa.SMALLINT(), nullable=True),
    sa.Column('v_30_49', sa.SMALLINT(), nullable=True),
    sa.Column('v_50_64', sa.SMALLINT(), nullable=True),
    sa.Column('v_65_74', sa.SMALLINT(), nullable=True),
    sa.Column('v_75', sa.SMALLINT(), nullable=True),
    sa.PrimaryKeyConstraint('vuosi', 'kunta', 'xyind'),
    schema='grid_globals'
    )
    op.create_table('citizen_traffic_stress',
    sa.Column('mun', sa.Integer(), nullable=False),
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('jalkapyora', sa.Float(), nullable=False),
    sa.Column('bussi', sa.Float(), nullable=False),
    sa.Column('raide', sa.Float(), nullable=False),
    sa.Column('hlauto', sa.Float(), nullable=False),
    sa.Column('muu', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('mun', 'scenario', 'year'),
    schema='traffic'
    )
    op.create_index('personal_traffic_index', 'citizen_traffic_stress', ['mun', 'scenario', 'year'], unique=False, schema='traffic')
    op.create_table('hlt_2015_tre',
    sa.Column('zone', sa.Integer(), nullable=False),
    sa.Column('jalkapyora', sa.Float(), nullable=False),
    sa.Column('bussi', sa.Float(), nullable=False),
    sa.Column('raide', sa.Float(), nullable=False),
    sa.Column('hlauto', sa.Float(), nullable=False),
    sa.Column('muu', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('zone'),
    schema='traffic'
    )
    op.create_table('hlt_kmchange',
    sa.Column('zone', sa.Integer(), nullable=False),
    sa.Column('jalkapyora', sa.Float(), nullable=False),
    sa.Column('bussi', sa.Float(), nullable=False),
    sa.Column('raide', sa.Float(), nullable=False),
    sa.Column('hlauto', sa.Float(), nullable=False),
    sa.Column('muu', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('zone'),
    schema='traffic'
    )
    op.create_table('hlt_lookup',
    sa.Column('mun', sa.Integer(), nullable=False),
    sa.Column('hlt_table', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.PrimaryKeyConstraint('mun'),
    schema='traffic'
    )
    op.create_table('hlt_workshare',
    sa.Column('zone', sa.Integer(), nullable=False),
    sa.Column('jalkapyora', sa.Float(), nullable=False),
    sa.Column('bussi', sa.Float(), nullable=False),
    sa.Column('raide', sa.Float(), nullable=False),
    sa.Column('hlauto', sa.Float(), nullable=False),
    sa.Column('muu', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('zone'),
    schema='traffic'
    )
    op.create_table('industr_performance',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('kmuoto', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('teoll_kaivos', sa.Integer(), nullable=False),
    sa.Column('teoll_elint', sa.Integer(), nullable=False),
    sa.Column('teoll_tekst', sa.Integer(), nullable=False),
    sa.Column('teoll_puu', sa.Integer(), nullable=False),
    sa.Column('teoll_paper', sa.Integer(), nullable=False),
    sa.Column('teoll_kemia', sa.Integer(), nullable=False),
    sa.Column('teoll_miner', sa.Integer(), nullable=False),
    sa.Column('teoll_mjalos', sa.Integer(), nullable=False),
    sa.Column('teoll_metal', sa.Integer(), nullable=False),
    sa.Column('teoll_kone', sa.Integer(), nullable=False),
    sa.Column('teoll_muu', sa.Integer(), nullable=False),
    sa.Column('teoll_energ', sa.Integer(), nullable=False),
    sa.Column('teoll_vesi', sa.Integer(), nullable=False),
    sa.Column('teoll_yhdysk', sa.Integer(), nullable=False),
    sa.Column('varast', sa.Integer(), nullable=False),
    sa.Column('teoll', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year', 'kmuoto'),
    schema='traffic'
    )
    op.create_index('industry_performance_index', 'industr_performance', ['scenario', 'year', 'kmuoto'], unique=False, schema='traffic')
    op.create_table('industr_transport_km',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('kmuoto', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('teoll_kaivos', sa.Integer(), nullable=False),
    sa.Column('teoll_elint', sa.Integer(), nullable=False),
    sa.Column('teoll_tekst', sa.Integer(), nullable=False),
    sa.Column('teoll_puu', sa.Integer(), nullable=False),
    sa.Column('teoll_paper', sa.Integer(), nullable=False),
    sa.Column('teoll_kemia', sa.Integer(), nullable=False),
    sa.Column('teoll_miner', sa.Integer(), nullable=False),
    sa.Column('teoll_mjalos', sa.Integer(), nullable=False),
    sa.Column('teoll_metal', sa.Integer(), nullable=False),
    sa.Column('teoll_kone', sa.Integer(), nullable=False),
    sa.Column('teoll_muu', sa.Integer(), nullable=False),
    sa.Column('teoll_energ', sa.Integer(), nullable=False),
    sa.Column('teoll_vesi', sa.Integer(), nullable=False),
    sa.Column('teoll_yhdysk', sa.Integer(), nullable=False),
    sa.Column('varast', sa.Integer(), nullable=False),
    sa.Column('teoll', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year', 'kmuoto'),
    schema='traffic'
    )
    op.create_index('industry_performance_km_index', 'industr_transport_km', ['scenario', 'year', 'kmuoto'], unique=False, schema='traffic')
    op.create_table('mode_power_distribution',
    sa.Column('mun', sa.Integer(), nullable=False),
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('kmuoto', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('kvoima_bensiini', sa.Float(), nullable=False),
    sa.Column('kvoima_etanoli', sa.Float(), nullable=False),
    sa.Column('kvoima_diesel', sa.Float(), nullable=False),
    sa.Column('kvoima_kaasu', sa.Float(), nullable=False),
    sa.Column('kvoima_phev_b', sa.Float(), nullable=False),
    sa.Column('kvoima_phev_d', sa.Float(), nullable=False),
    sa.Column('kvoima_ev', sa.Float(), nullable=False),
    sa.Column('kvoima_vety', sa.Float(), nullable=False),
    sa.Column('kvoima_muut', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('mun', 'scenario', 'year', 'kmuoto'),
    schema='traffic'
    )
    op.create_index('mode_power_distribution_index', 'mode_power_distribution', ['scenario', 'year', 'kmuoto'], unique=False, schema='traffic')
    op.create_table('power_fossil_share',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('share', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year'),
    schema='traffic'
    )
    op.create_index('power_fossil_share_index', 'power_fossil_share', ['scenario', 'year'], unique=False, schema='traffic')
    op.create_table('power_kwhkm',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('kmuoto', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('kvoima_bensiini', sa.Float(), nullable=False),
    sa.Column('kvoima_etanoli', sa.Float(), nullable=False),
    sa.Column('kvoima_diesel', sa.Float(), nullable=False),
    sa.Column('kvoima_kaasu', sa.Float(), nullable=False),
    sa.Column('kvoima_phev_b', sa.Float(), nullable=False),
    sa.Column('kvoima_phev_d', sa.Float(), nullable=False),
    sa.Column('kvoima_ev', sa.Float(), nullable=False),
    sa.Column('kvoima_vety', sa.Float(), nullable=False),
    sa.Column('kvoima_muut', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year', 'kmuoto'),
    schema='traffic'
    )
    op.create_index('power_kwhkm_index', 'power_kwhkm', ['scenario', 'year', 'kmuoto'], unique=False, schema='traffic')
    op.create_table('service_performance',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('kmuoto', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('myymal_hyper', sa.Float(), nullable=False),
    sa.Column('myymal_super', sa.Float(), nullable=False),
    sa.Column('myymal_pien', sa.Float(), nullable=False),
    sa.Column('myymal_muu', sa.Float(), nullable=False),
    sa.Column('majoit', sa.Float(), nullable=False),
    sa.Column('asla', sa.Float(), nullable=False),
    sa.Column('ravint', sa.Float(), nullable=False),
    sa.Column('tsto', sa.Float(), nullable=False),
    sa.Column('liiken', sa.Float(), nullable=False),
    sa.Column('hoito', sa.Float(), nullable=False),
    sa.Column('kokoon', sa.Float(), nullable=False),
    sa.Column('opetus', sa.Float(), nullable=False),
    sa.Column('muut', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year', 'kmuoto'),
    schema='traffic'
    )
    op.create_index('service_performance_index', 'service_performance', ['scenario', 'year', 'kmuoto'], unique=False, schema='traffic')
    op.create_table('services_transport_km',
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('kmuoto', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('myymal_hyper', sa.Integer(), nullable=False),
    sa.Column('myymal_super', sa.Integer(), nullable=False),
    sa.Column('myymal_pien', sa.Integer(), nullable=False),
    sa.Column('myymal_muu', sa.Integer(), nullable=False),
    sa.Column('majoit', sa.Integer(), nullable=False),
    sa.Column('asla', sa.Integer(), nullable=False),
    sa.Column('ravint', sa.Integer(), nullable=False),
    sa.Column('tsto', sa.Integer(), nullable=False),
    sa.Column('liiken', sa.Integer(), nullable=False),
    sa.Column('hoito', sa.Integer(), nullable=False),
    sa.Column('kokoon', sa.Integer(), nullable=False),
    sa.Column('opetus', sa.Integer(), nullable=False),
    sa.Column('muut', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('scenario', 'year', 'kmuoto'),
    schema='traffic'
    )
    op.create_index('service_transport_index', 'services_transport_km', ['scenario', 'year', 'kmuoto'], unique=False, schema='traffic')
    op.create_table('workers_traffic_stress',
    sa.Column('mun', sa.Integer(), nullable=False),
    sa.Column('scenario', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('jalkapyora', sa.Float(), nullable=False),
    sa.Column('bussi', sa.Float(), nullable=False),
    sa.Column('raide', sa.Float(), nullable=False),
    sa.Column('hlauto', sa.Float(), nullable=False),
    sa.Column('muu', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('mun', 'scenario', 'year'),
    schema='traffic'
    )
    op.create_index('workers_traffic_stress_index', 'workers_traffic_stress', ['mun', 'scenario', 'year'], unique=False, schema='traffic')

def downgrade() -> None:
    op.drop_index('workers_traffic_stress_index', table_name='workers_traffic_stress', schema='traffic')
    op.drop_table('workers_traffic_stress', schema='traffic')
    op.drop_index('service_transport_index', table_name='services_transport_km', schema='traffic')
    op.drop_table('services_transport_km', schema='traffic')
    op.drop_index('service_performance_index', table_name='service_performance', schema='traffic')
    op.drop_table('service_performance', schema='traffic')
    op.drop_index('power_kwhkm_index', table_name='power_kwhkm', schema='traffic')
    op.drop_table('power_kwhkm', schema='traffic')
    op.drop_index('power_fossil_share_index', table_name='power_fossil_share', schema='traffic')
    op.drop_table('power_fossil_share', schema='traffic')
    op.drop_index('mode_power_distribution_index', table_name='mode_power_distribution', schema='traffic')
    op.drop_table('mode_power_distribution', schema='traffic')
    op.drop_index('industry_performance_km_index', table_name='industr_transport_km', schema='traffic')
    op.drop_table('industr_transport_km', schema='traffic')
    op.drop_index('industry_performance_index', table_name='industr_performance', schema='traffic')
    op.drop_table('industr_performance', schema='traffic')
    op.drop_table('hlt_workshare', schema='traffic')
    op.drop_table('hlt_lookup', schema='traffic')
    op.drop_table('hlt_kmchange', schema='traffic')
    op.drop_table('hlt_2015_tre', schema='traffic')
    op.drop_index('personal_traffic_index', table_name='citizen_traffic_stress', schema='traffic')
    op.drop_table('citizen_traffic_stress', schema='traffic')
    op.drop_table('pop', schema='grid_globals')
    op.drop_table('employ', schema='grid_globals')
    op.drop_table('clc', schema='grid_globals')
    op.drop_table('buildings', schema='grid_globals')
    op.drop_index('spaces_gco2kwh_index', table_name='spaces_gco2kwh', schema='energy')
    op.drop_table('spaces_gco2kwh', schema='energy')
    op.drop_index('heating_degree_days_index', table_name='heating_degree_days', schema='energy')
    op.drop_table('heating_degree_days', schema='energy')
    op.drop_index('heat_source_change_index', table_name='heat_source_change', schema='energy')
    op.drop_table('heat_source_change', schema='energy')
    op.drop_index('electricity_home_percapita_index', table_name='electricity_home_percapita', schema='energy')
    op.drop_table('electricity_home_percapita', schema='energy')
    op.drop_index('electricity_index', table_name='electricity', schema='energy')
    op.drop_table('electricity', schema='energy')
    op.drop_index('district_heating_index', table_name='district_heating', schema='energy')
    op.drop_table('district_heating', schema='energy')
    op.drop_index('cooling_gco2kwh_index', table_name='cooling_gco2kwh', schema='energy')
    op.drop_table('cooling_gco2kwh', schema='energy')
    op.drop_index('idx_grid_WKT', table_name='grid', schema='delineations', postgresql_using='gist')
    op.drop_table('grid', schema='delineations')
    op.drop_index('idx_centroids_WKT', table_name='centroids', schema='delineations', postgresql_using='gist')
    op.drop_table('centroids', schema='delineations')
    op.drop_index('water_kwhm2_index', table_name='water_kwhm2', schema='built')
    op.drop_table('water_kwhm2', schema='built')
    op.drop_index('spaces_kwhm2_index', table_name='spaces_kwhm2', schema='built')
    op.drop_table('spaces_kwhm2', schema='built')
    op.drop_index('spaces_efficiency_index', table_name='spaces_efficiency', schema='built')
    op.drop_table('spaces_efficiency', schema='built')
    op.drop_index('occupancy_index', table_name='occupancy', schema='built')
    op.drop_table('occupancy', schema='built')
    op.drop_table('iwhs_sizes', schema='built')
    op.drop_index('electricity_property_kwhkm_index', table_name='electricity_property_kwhm2', schema='built')
    op.drop_table('electricity_property_kwhm2', schema='built')
    op.drop_index('electricity_property_change_index', table_name='electricity_property_change', schema='built')
    op.drop_table('electricity_property_change', schema='built')
    op.drop_index('electricity_industry_index', table_name='electricity_iwhs_kwhm2', schema='built')
    op.drop_table('electricity_iwhs_kwhm2', schema='built')
    op.drop_index('electricity_home_light_index', table_name='electricity_home_light', schema='built')
    op.drop_table('electricity_home_light', schema='built')
    op.drop_index('electricity_home_device_index', table_name='electricity_home_device', schema='built')
    op.drop_table('electricity_home_device', schema='built')
    op.drop_index('distribution_heating_system_index', table_name='distribution_heating_systems', schema='built')
    op.drop_table('distribution_heating_systems', schema='built')
    op.drop_index('cooling_proportions_index', table_name='cooling_proportions_kwhm2', schema='built')
    op.drop_table('cooling_proportions_kwhm2', schema='built')
    op.drop_index('build_renovation_energy_index', table_name='build_renovation_energy_gco2m2', schema='built')
    op.drop_table('build_renovation_energy_gco2m2', schema='built')
    op.drop_index('build_rebuilding_share_index', table_name='build_rebuilding_share', schema='built')
    op.drop_table('build_rebuilding_share', schema='built')
    op.drop_index('build_rebuilding_energy_index', table_name='build_rebuilding_energy_gco2m2', schema='built')
    op.drop_table('build_rebuilding_energy_gco2m2', schema='built')
    op.drop_index('construction_index', table_name='build_new_construction_energy_gco2m2', schema='built')
    op.drop_table('build_new_construction_energy_gco2m2', schema='built')
    op.drop_index('build_materia_index', table_name='build_materia_gco2m2', schema='built')
    op.drop_table('build_materia_gco2m2', schema='built')
    op.drop_index('build_demolish_index', table_name='build_demolish_energy_gco2m2', schema='built')
    op.drop_table('build_demolish_energy_gco2m2', schema='built')
    op.execute("DROP SCHEMA built")
    op.execute("DROP SCHEMA delineations")
    op.execute("DROP SCHEMA energy")
    op.execute("DROP SCHEMA grid_globals")
    op.execute("DROP SCHEMA traffic")
