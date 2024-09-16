"""Create functions

Revision ID: 30e2e5e7b557
Revises: a885f87c8335
Create Date: 2024-09-14 13:45:52.782949

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30e2e5e7b557'
down_revision: Union[str, None] = 'a2d00dad3fc6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        /* Uudisrakentaminen (energia) | Construction of new buildings (energy)

        YKR-ruudun laskentavuoden uudisrakentamisen energian kasvihuonekaasupäästöt [CO2-ekv/a] lasketaan seuraavasti:

            rak_uusi_energia_co2 = rakennus_ala * rak_energia_gco2m2

        YKR-ruudun laskentavuoden uudisrakentamisen rakennustuotteiden kasvihuonekaasupäästöt rak_uusi_materia_co2 [CO2-ekv/a] lasketaan seuraavasti:
        
            rak_uusi_materia_co2 = rakennus_ala * rak_materia_gco2m2
        */

        CREATE SCHEMA IF NOT EXISTS functions;
        DROP FUNCTION IF EXISTS functions.CO2_BuildConstruct;
        CREATE OR REPLACE FUNCTION
        functions.CO2_BuildConstruct(
            floorSpace real, -- Rakennustyypin tietyn ikäluokan kerrosala YKR-ruudussa laskentavuonna [m2]. Lukuarvo riippuu laskentavuodesta ja rakennuksen tyypistä.
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            buildingType varchar, -- Rakennustyyppi, esim. 'erpien', 'rivita'
            calculationScenario varchar -- PITKO:n mukainen kehitysskenaario
        )
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer;
            construction_energy_gco2m2 real; -- Rakennustyypin rakentamisvaiheen työmaatoimintojen ja kuljetusten kasvihuonekaasujen ominaispäästöjä yhtä rakennettua kerrosneliötä kohti [gCO2-ekv/m2]. Arvo riippuu taustaskenaariosta, tarkasteluvuodesta ja rakennustyypistä.
            construction_materials_gco2m2 real; -- Rakennustyypin rakentamiseen tarvittujen rakennustuotteiden tuotantoprosessin välillisiä kasvihuonekaasujen ominaispäästöjä yhtä rakennettua kerrosneliötä kohti [gCO2-ekv/m2]. Arvo riippuu taustaskenaariosta, tarkasteluvuodesta ja rakennustyypistä.
        BEGIN

        /* Returning zero, if grid cell has 0, -1 or NULL built floor area */
        IF floorSpace <= 0 OR floorSpace IS NULL THEN RETURN 0;
        /* In other cases continue with the calculation */
        ELSE
            calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
        END;

        /* If the year of construction is not the current year of calculation, return 0 */
        --      IF rakennusvuosi != year THEN
        --        RETURN 0;
                /* Muussa tapauksessa jatka laskentaan */
                /* In other cases, continue */
        --    ELSE

            /* Haetaan laskentavuoden ja kehitysskenaarion perusteella rakennustyyppikohtaiset uudisrakentamisen energiankulutuksen kasvihuonekaasupäästöt */
            /* Get the unit emissions for energy consumption of construction by year of building, scenario and building type */
            EXECUTE 'SELECT ' || buildingType || ' FROM built.build_new_construction_energy_gco2m2
                WHERE year = $1 AND scenario = $2 LIMIT 1'
                INTO construction_energy_gco2m2 USING calculationYear, calculationScenario;
            
            /* Haetaan laskentavuoden ja kehitysskenaarion perusteella rakennustyyppikohtaiset uudisrakentamisen materiaalien valmistuksen kasvihuonekaasupäästöt */
            /* Get the unit emissions for production of materials for construction by year of building, scenario and building type */
            EXECUTE 'SELECT ' || CASE WHEN buildingType IN ('erpien', 'rivita', 'askert')
                THEN buildingType
                    ELSE 'muut'
                END || ' 
                    FROM built.build_materia_gco2m2
                    WHERE year = $1 AND scenario = $2 LIMIT 1'
                INTO construction_materials_gco2m2
                    USING calculationYear, calculationScenario;

            /* Lasketaan ja palautetaan päästöt CO2-ekvivalenttia [gCO2-ekv/v] */
            /* Calculate and return emissions as CO2-equivalents [gCO2-ekv/a] */
            RETURN floorSpace * 
                (COALESCE(construction_energy_gco2m2,0) + COALESCE(construction_materials_gco2m2, 0));
        --    END IF;
        END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Rakennusten purkaminen (energia) | Demolition of buildings (energy)
        Rakennuksen elinkaaren katsotaan päättyvän, kun rakennus on purettu ja tontilta on
        kuljetettu pois kaikki rakennusmateriaalit ja tontti on valmis seuraavaa käyttöä varten.
        Päästölaskennassa huomioidaan rakennuksen purkutyön, puretun materiaalin jatkokäsittelykuljetusten
        ja sen loppukäsittelyn ja -sijoituksen energiaperäiset kasvihuonekaasupäästöt rak_purku_energia_co2 [CO2-ekv/a] seuraavasti

            rak_purku_energia_co2 = rakennukset_poistuma * rak_purku_energia_gco2m2
        */

        CREATE SCHEMA IF NOT EXISTS functions;
        DROP FUNCTION IF EXISTS functions.CO2_BuildDemolish;
        CREATE OR REPLACE FUNCTION
        functions.CO2_BuildDemolish(
            buildingsRemoval real, -- rakennustyypin (erpien, rivita, askert, liike, tsto, liiken, hoito, kokoon, opetus, teoll, varast, muut) kerrosalan poistuma YKR-ruudussa laskentavuonna [m2].
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            buildingType varchar, -- Rakennustyyppi | Building type. esim. | e.g. 'erpien', 'rivita'
            calculationScenario varchar -- PITKO-kehitysskenaario | PITKO development scenario
        )
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer;
            rak_purku_energia_gco2m2 real; -- [gCO2-ekv/m2] on rakennustyypin purkamisen, puretun materiaalin kuljetusten ja niiden käsittelyn kasvihuonekaasujen ominaispäästöt yhtä purettua kerroskerrosneliötä kohti. Lukuarvo riippuu taustaskenaariosta, tarkasteluvuodesta ja rakennustyypistä.
        BEGIN

        /* Palautetaan nolla, mikäli ruudun kerrosala on 0, -1 tai NULL */
        /* Returning zero, if grid cell has 0, -1 or NULL built floor area */
        IF buildingsRemoval <= 0 OR buildingsRemoval IS NULL THEN
            RETURN 0;
        /* Muussa tapauksessa jatka laskentaan */
        /* In other cases continue with the calculation */
        ELSE
            calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
            END;
            /* Haetaan laskentavuoden ja kehitysskenaarion perusteella rakennustyyppikohtaiset uudisrakentamisen energiankulutuksen kasvihuonekaasupäästöt */
            /* Get the unit emissions for energy consumption of construction by year of building, scenario and building type */
            EXECUTE 'SELECT ' || buildingType || ' 
                FROM built.build_demolish_energy_gco2m2 WHERE scenario = $1 AND year = $2'
                INTO rak_purku_energia_gco2m2
                    USING calculationScenario, calculationYear;
            
            /* Lasketaan ja palautetaan päästöt CO2-ekvivalentteina [gCO2-ekv/v] */
            /* Calculate and return emissions as CO2-equivalents [gCO2-ekv/a] */
            RETURN buildingsRemoval * COALESCE(rak_purku_energia_gco2m2, 0);

        END IF;

        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Korjausrakentamisen ja saneeraamisen päästöt | Emissions from renovations and large scale overhauls of buildings

        Rakennusten käytön aikana tehtävien tavanomaisten korjausten ja rakennustuotteiden vaihtojen energian käytön kasvihuonekaasupäästöt rak_korj_energia_co2 [CO2-ekv/a] ovat

            rak_korj_energia_co2= rakennus_ala* rak_korj_energia_gco2m2

        YKR-ruudun rakennusten laajamittaisen korjausten energian käytön laskentavuonna aiheuttamat kasvihuonekaasupäästöt rak_saneer_energia_co2 [t CO2-ekv/a] lasketaan kaavalla

            rak_saneer_energia_co2 = rakennus_ala * rak_saneer_osuus * rak_saneer_energia_gco2m2 * muunto_massa

        Kummassakaan tarkastelussa ei oteta vielä tässä vaiheessa huomioon korjaamisessa tarvittavien materiaalien valmistuksen aiheuttamia välillisiä kasvihuonekaasupäästöjä.

        */
        CREATE SCHEMA IF NOT EXISTS functions;
        DROP FUNCTION IF EXISTS functions.CO2_BuildRenovate;
        CREATE OR REPLACE FUNCTION
        functions.CO2_BuildRenovate(
            floorSpace real, -- Rakennustyypin (erpien, rivita, askert, liike, tsto, liiken, hoito, kokoon, opetus, teoll, varast, muut) ikäluokkakohtainen kerrosala YKR-ruudussa laskentavuonna [m2]. Lukuarvo riippuu laskentavuodesta sekä rakennuksen tyypistä ja ikäluokasta.
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            buildingType varchar,  -- Rakennustyyppi | Building type. esim. | e.g. 'erpien', 'rivita'
            buildingYear integer, -- Rakennusvuosikymmen tai -vuosi (2017 alkaen) | Building decade or year (2017 onwards)
            calculationScenario varchar) -- PITKO-kehitysskenaario | PITKO development scenario
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer;
            rak_korj_energia_gco2m2 real; -- Tarkasteltavan rakennustyypin pienimuotoisten korjausten työmaatoimintojen ja kuljetusten kasvihuonekaasun ominaispäästöt yhtä kerrosneliötä kohti laskentavuonna [gCO2-ekv/m2]. Riippuu taustaskenaariosta, laskentavuodesta ja rakennustyypistä.
            rak_saneer_energia_gco2m2  real; -- Tarkasteltavan rakennustyypin laajamittaisen korjausrakentamisen työmaatoimintojen ja kuljetusten kasvihuonekaasun ominaispäästöt yhtä kerroskerrosneliötä kohti laskentavuonna [gCO2-ekv/m2]. Riippuu taustaskenaariosta, laskentavuodesta ja rakennustyypistä.
            rak_saneer_osuus real; -- Rakennustyypin ikäluokkakohtainen kerrosalaosuus, johon tehdään laskentavuoden aikana laajamittaisia korjausrakentamista [ei yksikköä]. Lukuarvo riippuu taustaskenaariosta, laskentavuodesta sekä rakennuksen ikäluokasta ja tyypistä.
        BEGIN
            IF floorSpace <= 0 OR floorSpace IS NULL THEN
                RETURN 0;
            ELSE
            
                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                    WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                    ELSE calculationYears[1]
                END;

                /* Korjausrakentamisen ominaispäästöt */
                EXECUTE 'SELECT ' || buildingType || ' FROM built.build_renovation_energy_gco2m2 WHERE scenario = $1 AND year = $2'
                    INTO rak_korj_energia_gco2m2  USING calculationScenario, calculationYear;
                /* Saneerauksen ominaispäästöt ja vuosittainen kattavuus */
                EXECUTE 'SELECT ' || buildingType || ' FROM built.build_rebuilding_energy_gco2m2 WHERE scenario = $1 AND year = $2'
                    INTO rak_saneer_energia_gco2m2  USING calculationScenario, calculationYear;
                EXECUTE 'SELECT ' || buildingType || ' FROM built.build_rebuilding_share WHERE scenario = $1 AND rakv = $2 AND year = $3'
                    INTO rak_saneer_osuus USING calculationScenario, buildingYear, calculationYear;

                RETURN floorSpace *
                    (COALESCE(rak_korj_energia_gco2m2, 0) + COALESCE(rak_saneer_energia_gco2m2, 0) * COALESCE(rak_saneer_osuus,0));
                
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Sähkön käyttö, kotitaloudet | Electricity consumption, households

        Kotitalouksien sähkön käyttö muuhun kuin asuinrakennusten lämmitykseen, jäähdytykseen ja kiinteistön laitteisiin sahko_koti_kwh [kWh/a] lasketaan kaavalla

            sahko_koti_kwh = rakennus_ala * (sahko_koti_laite + sahko_koti_valo) + v_yht * sahko_koti_as

        Kotitalouksien muuhun kuin lämmitykseen ja kiinteistösähköön käytetyn sähkön kasvihuonekaasupäästöt sahko_koti_co2 [CO2-ekv/a] ovat 

            sahko_koti_co2 = sahko_koti_kwh  * sahko_gco2kwh
        */

        CREATE SCHEMA IF NOT EXISTS functions;
        DROP FUNCTION IF EXISTS functions.CO2_ElectricityHousehold;
        CREATE OR REPLACE FUNCTION
        functions.CO2_ElectricityHousehold(
            municipality int,
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            calculationScenario varchar, -- PITKO-kehitysskenaario | PITKO development scenario
            area_or_pop real, -- Rakennustyypin ikäluokkakohtainen kerrosala YKR-ruudussa laskentavuonna [m2] tai väestö laskentavuonna.
            buildingType varchar -- Rakennustyyppi | Building type. esim. | e.g. 'erpien', 'rivita'
        )
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer;
            result_gco2 real;
        BEGIN
            IF area_or_pop <= 0 OR area_or_pop IS NULL THEN
                RETURN 0;
            ELSE

                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                    WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                    ELSE calculationYears[1]
                END;

            IF buildingType IS NULL THEN
                    EXECUTE FORMAT(
                        'WITH electricity_home_percapita AS (
                            -- Asukkaiden lisävaikutus asunnon sähkön kulutukseen. [kWh/as/a].
                            SELECT sahko_koti_as AS kwh
                            FROM energy.electricity_home_percapita sas
                            WHERE sas.year = %1$L
                                AND sas.scenario = %2$L
                                AND sas.mun = %4$L
                        ), electricity_gco2kwh AS (
                            -- Kulutetun sähkön ominaispäästökerroin [gCO2-ekv/kWh].
                            SELECT el.gco2kwh::int AS gco2
                            FROM energy.electricity el
                                WHERE el.year = %1$L
                                AND el.scenario = %2$L
                                AND el.metodi = ''em''
                                AND el.paastolaji = ''tuotanto''
                        )
                        SELECT %3$L * percapita.kwh * gco2kwh.gco2
                        FROM electricity_home_percapita percapita, electricity_gco2kwh gco2kwh
                        '
                    , calculationYear, calculationScenario, area_or_pop, municipality
                    ) INTO result_gco2;
            
            ELSE 
                    EXECUTE FORMAT(
                        'WITH electricity_home_devices AS (
                            -- Rakennustyyppikohtainen laitesähkön keskimääräinen peruskulutus [kWh/m2/a]
                            SELECT %3$I::int AS kwh
                            FROM built.electricity_home_device WHERE scenario = %2$L AND year = %1$L
                        ), electricity_home_lighting AS (
                            -- Rakennustyyppikohtainen sisävalaistuksen sähkön käyttö kerrosneliötä kohti huomioiden tekniikan ja muuhun valaistukseen liittyvän sähkön käytön kehityksen [kWh/m2/a]
                            SELECT %3$I::int AS kwh
                            FROM built.electricity_home_light WHERE scenario = %2$L AND year = %1$L
                        ), electricity_gco2kwh AS (
                            SELECT el.gco2kwh::int AS gco2 -- Kulutetun sähkön ominaispäästökerroin [gCO2-ekv/kWh].
                            FROM energy.electricity el
                                WHERE el.year = %1$L
                                AND el.scenario = %2$L
                                AND el.metodi = ''em''
                                AND el.paastolaji = ''tuotanto''
                        )
                        SELECT  %4$L * (devices.kwh + lights.kwh) * gco2kwh.gco2
                        FROM electricity_home_devices devices,   
                            electricity_home_lighting lights,
                            electricity_gco2kwh gco2kwh
                        '
                    , calculationYear,
                    calculationScenario,
                    buildingType,
                    area_or_pop
                    ) INTO result_gco2;
            
            END IF;

            END IF;
            RETURN result_gco2;

        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Sähkön käyttö, teollisuus, varastot ja palvelut | Electricity consumption, industry, warehouses and services

        Palvelusektorin sekä teollisuuden ja varastojen sähkön käyttö muuhun kuin rakennusten lämmitykseen, jäähdytykseen ja kiinteistön laitteisiin sahko_palv_kwh [kWh/a] perustuu kaavaan

            sahko_ptv_kwh  = rakennus_ala * sahko_ptv_kwhm2

        Palvelusektorin sekä teollisuuden ja varastojen muuhun lämmitykseen ja kiinteistöshköön käytetyn sähkön kasvihuonekaasupäästöt sahko_palv_co2 [CO2-ekv/a] ovat 

            sahko_ptv_co2 = sahko_ptv_kwh  * sahko_gco2kwh

        Teollisuus- ja varastorakennusten sähkön käyttö sisältää myös niiden kiinteistösähkön kulutuksen.

        */

        CREATE SCHEMA IF NOT EXISTS functions;
        DROP FUNCTION IF EXISTS functions.CO2_ElectricityIWHS;
        CREATE OR REPLACE FUNCTION
        functions.CO2_ElectricityIWHS(
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            calculationScenario varchar, -- PITKO-kehitysskenaario | PITKO development scenario
            floorSpace real, -- rakennustyypin kerrosala YKR-ruudussa laskentavuonna [m2]. Riippuu laskentavuodesta, rakennuksen tyypistä ja ikäluokasta.
            buildingType varchar -- Rakennustyyppi | Building type. esim. | e.g. 'erpien', 'rivita'
        )
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer;
            services varchar[] default ARRAY['myymal_hyper', 'myymal_super', 'myymal_pien', 'myymal_muu', 'myymal', 'majoit', 'asla', 'ravint', 'tsto', 'liiken', 'hoito', 'kokoon', 'opetus', 'muut'];
            result_gco2 real;
        BEGIN

            IF floorSpace <= 0
                OR floorSpace IS NULL THEN
                RETURN 0;
            ELSE

                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                    WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                    ELSE calculationYears[1]
                END;

                EXECUTE FORMAT('
                    WITH 
                    electricity_gco2kwh AS (
                        -- Kulutetun sähkön ominaispäästökerroin [gCO2-ekv/kWh]
                        SELECT el.gco2kwh::real AS gco2 
                        FROM energy.electricity el
                            WHERE el.year = %3$L 
                            AND el.scenario = %2$L
                            AND el.metodi = ''em''
                            AND el.paastolaji = ''tuotanto'' LIMIT 1
                    )
                    -- rakennustyypissä tapahtuvan toiminnan sähköintensiteetti kerrosneliömetriä kohti [kWh/m2]
                    SELECT ry.%1$I * %4$L::int * el.gco2
                    FROM built.electricity_iwhs_kwhm2 ry, electricity_gco2kwh el
                        WHERE ry.scenario = %2$L AND ry.year = %3$L LIMIT 1',
                    buildingType,
                    calculationScenario,
                    calculationYear,
                    floorSpace
                ) INTO result_gco2;
                
                RETURN result_gco2;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Kiinteistösähkön kulutus | Consupmtion of property tech electricity

        YKR-ruudun rakennusten liittyvä kiinteistösähkön käyttö sahko_kiinteisto_kwh [kWh/a] lasketaan kaavalla:
            sahko_kiinteisto_kwh = rakennus_ala * sahko_kiinteisto_kwhm2 * sahko_kiinteisto_muutos

        Kiinteistösähkön kasvihuonekaasupäästöt sahko_kiinteisto_co2 [CO2-ekv/a] ovat:
            sahko_kiinteisto_co2 = sahko_kiinteisto_kwh * sahko_gco2kwh

        */

        CREATE SCHEMA IF NOT EXISTS functions;
        DROP FUNCTION IF EXISTS functions.CO2_ElectricityProperty;
        CREATE OR REPLACE FUNCTION
        functions.CO2_ElectricityProperty(
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            calculationScenario varchar, -- PITKO-kehitysskenaario | PITKO development scenario
            floorSpace real, -- Rakennustyypin ikäluokkakohtainen kerrosala YKR-ruudussa laskentavuonna. Lukuarvo riippuu laskentavuodesta sekä rakennuksen tyypistä ja ikäluokasta [m2]
            buildingType varchar, -- Rakennustyyppi | Building type. esim. | e.g. 'erpien', 'rivita'
            buildingYear integer -- Rakennusvuosikymmen tai -vuosi (2017 alkaen) | Building decade or year (2017 onwards)
        )
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer;
            result_gco2 real;
            sahko_kiinteisto_muutos real; -- Rakennustyypin ikäluokkakohtainen keskimääräisen kiinteistösähkön kulutuksen muutos tarkasteluvuonna [Ei yksikköä]. Lukuarvo riippuu laskentavuodesta ja rakennuksen ikäluokasta
        BEGIN
            
            /* Palautetaan nolla, mikäli ruudun kerrosala on 0, -1 tai NULL */
            /* Returning zero, if grid cell has 0, -1 or NULL built floor area */
            IF floorSpace <= 0 OR floorSpace IS NULL THEN
                RETURN 0;
            /* Muussa tapauksessa jatka laskentaan */
            /* In other cases continue with the calculation */
            ELSE

                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
                END;

                EXECUTE FORMAT(
                'WITH electricity_property_khwm2 AS (
                    -- Kiinteistöjen sähkönkulutus kerrosalaa kohti
                    -- Electricity consumption of integrated property technology
                    SELECT sahko_kiinteisto_kwhm2 AS kwh
                    FROM built.electricity_property_kwhm2
                    WHERE scenario = %2$L
                        AND rakennus_tyyppi = %3$L
                        AND rakv = %4$L
                        LIMIT 1
                ), electricity_property_change AS (
                    -- Kiinteistöjen sähkönkulutuksen muutos rakennusten rakennusvuosikymmenittäin
                    -- Change of property electricity consumption according to year of building
                
                    SELECT %4$I as change
                        FROM built.electricity_property_change
                        WHERE scenario = %2$L AND year = %1$L
                        LIMIT 1
                ),
                electricity_gco2kwh AS (
                    -- Kulutetun sähkön ominaispäästökerroin [gCO2-ekv/kWh].
                    SELECT el.gco2kwh::int AS gco2
                    FROM energy.electricity el
                        WHERE el.year = %1$L
                        AND el.scenario = %2$L
                        AND el.metodi = ''em''
                        AND el.paastolaji = ''tuotanto''
                )
                -- Lasketaan päästöt CO2-ekvivalentteina | Calculate emissions as gCO2-equivalents 
                SELECT %5$L * kwhm2.kwh * gco2kwh.gco2 * change.change
                FROM electricity_property_khwm2 kwhm2, electricity_gco2kwh gco2kwh, electricity_property_change change
                '
            , calculationYear,
            calculationScenario,
            buildingType,
            CASE WHEN buildingYear > 2010 THEN 2010 ELSE buildingYear end,
            floorSpace
            ) INTO result_gco2;
            
            RETURN result_gco2;

            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Rakennusten jäähdytys | Cooling of buildings 

        YKR-ruudun rakennusten jäähdytystarve jaahdytys_kwh [kWh/a] on:
            jaahdytys_kwh = rakennus_ala * jaahdytys_osuus * jaahdytys_kwhm2 * jaahdytys_muoto * jaahdytys_muutos

        Rakennusten jäähdytykseen tarvitun ostoenergian kasvihuonekaasupäästöt [CO2/a] ovat:
            jaahdytys_co2 = jaahdytys_kwh * (jmuoto_apu1 * sahko_gco2kwh + jmuoto_apu2 * jaahdytys_gco2kwh)

        */

        CREATE SCHEMA IF NOT EXISTS functions;
        DROP FUNCTION IF EXISTS functions.CO2_PropertyCooling;
        CREATE OR REPLACE FUNCTION
        functions.CO2_PropertyCooling(
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            calculationScenario varchar, -- PITKO-kehitysskenaario | PITKO development scenario
            floorSpace integer, -- Rakennustyypin tietyn ikäluokan kerrosala YKR-ruudussa laskentavuonna. Lukuarvo riippuu laskentavuodesta, rakennuksen tyypistä ja ikäluokasta [m2]
            buildingType varchar, -- Rakennustyyppi | Building type. esim. | e.g. 'erpien', 'rivita'
            buildingYear integer -- Rakennusvuosikymmen tai -vuosi (2017 alkaen) | Building decade or year (2017 onwards)
        )
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer;
            result_gco2 real;
            jaahdytys_kwhm2 real[]; -- Rakennustyypin ikäluokan jäähdytysenergian tarve yhtä kerrosneliötä kohti. Arvo riippuu taustaskenaariosta, rakennuksen tyypistä ja ikäluokasta [kWh/m2/a]
            jaahdytys_kwh real[]; -- Jäähdytyksen energiankulutus
            jaahdytys_co2 real[]; -- Jäähdytyksen kasvihuonekaasupäästöt [gCO2]
        BEGIN

            /* Palautetaan nolla, mikäli ruudun kerrosala on 0, -1 tai NULL */
            /* Returning zero, if grid cell has 0, -1 or NULL built floor area */
            IF floorSpace <= 0 OR floorSpace IS NULL THEN
                RETURN 0;
            /* Muussa tapauksessa jatka laskentaan */
            /* In other cases continue with the calculation */
            ELSE

                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
                END;

            /* Dummy-kertoimet jäähdytysmuodoille | Dummy multipliers by method of cooling */
            /* Jäähdytyksen ominaispäästökertoimet | Emission values for cooling */

            -- SELECT array[kaukok, sahko, pumput, muu] FROM energy.cooling_gco2kwh ej WHERE ej.year = calculationYear AND ej.scenario = calculationScenario INTO j_gco2kwh;
            -- SELECT array(SELECT unnest(array[0, 1, 1, 0]) * sahko_gco2kwh + unnest(j_gco2kwh) * unnest(array[1, 0, 0, 1])) INTO jaahdytys_gco2kwh;

                -- Tällä hetkellä luvut sähkön osalta, jaahdytys_sahko = aina 1
                EXECUTE FORMAT(
                    'WITH coolingchange AS
                        (SELECT 
                        CASE WHEN %1$L = ANY(%7$L) THEN (1 + (%3$L - 2017 - 1) * 0.0118) ELSE (1 + (%3$L - 2017 - 1) * 0.0273) END
                            AS change -- Jäähdytyksen määrän kasvu rakennustyypeittäin. [ei yksikköä]
                    ), coolingkwhm2 AS (
                        SELECT
                            jaahdytys_osuus -- Rakennusten jäähdytettävät osuudet | Proportion of different types of buildings cooled 
                            * jaahdytys_kwhm2 AS kwhm2 -- Jäähdytyksen energiankulutus kerrosalaa kohden || Energy consumption of cooling buildings per floor area
                        FROM built.cooling_proportions_kwhm2
                        WHERE scenario = %2$L AND rakennus_tyyppi = %4$L AND rakv = %5$L LIMIT 1
                    ), gco2kwh AS (
                        SELECT el.gco2kwh::int AS gco2
                        FROM energy.electricity el
                            WHERE el.year = %3$L
                            AND el.scenario = %2$L
                            AND el.metodi = ''em''
                            AND el.paastolaji = ''tuotanto''
                    )
                    SELECT coolingchange.change * coolingkwhm2.kwhm2 * %6$L * gco2kwh.gco2 
                        FROM coolingchange, coolingkwhm2, gco2kwh
                    ',
                    buildingType, calculationScenario, calculationYear, buildingType, buildingYear, floorSpace, ARRAY['erpien', 'rivita', 'askert', 'teoll', 'varast', 'muut']
                ) INTO result_gco2;
            
                RETURN result_gco2;

            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Rakennusten lämmitys | Heating of buildings

        Rakennusten lämmityksen kasvihuonekaasupäästöjen laskennalla tarkoitetaan tässä rakennusten nettomääräisen lämmitysenergian tarpeen arviointia.
        Tämä tarkoittaa rakennusten tilojen lämmittämiseen tarvittavaa energiaa, josta on vähennetty henkilöistä, valaistuksesta ja sähkölaitteista syntyvien lämpökuormien energia,
        poistoilmasta ja muista energiavirroista talteen otettu tilojen lämmityksessä hyödynnetty energia ja ikkunoiden kautta tuleva auringon säteilyenergia.

        Lämmitysmuotoihin – tai oikeammin lämmönlähteisiin – sisältyvät kauko- ja aluelämpö, kevyt polttoöljy, raskas polttoöljy, maakaasu, sähkölämmitys, puupolttoaineet, turve,
        kivihiili ja koksi, maalämpö ja muut vastaavat lämpöpumput sekä muut lämmitysmuodot. Jälkimmäiseen ryhmään sisältyvät myös tilastojen tuntemattomat lämmitysmuodot.

        YKR-ruudun buildingTypeen eri ikäluokkien lämmitysmuotojen tilojen nettolämmitystarpeet tilat_lammitystarve [kWh/a] lasketaan seuraavalla kaavalla.
        
            tilat_lammitystarve =  floorSpace * tilat_kwhm2  * lammitystarve_vuosi / lammitystarve_vertailu / lammitystarve_korjaus_vkunta

        Jos tarkasteltavan alueen rakennusten tyyppi-, ikäluokka- ja lämmitysmuotojakauma perustuu kunnan omaan paikkatietopohjaiseen aineistoon,
        floorSpace -tieto on lämmitysmuotokohtainen. Tämä tarkempi laskentatapa ottaa huomioon keskimääräiseen jakaumaan perustuvaa laskentaa paremmin huomioon lämmitysmuotojakauman ruutukohtaiset erot.
        Muutoin voidaan käyttää esilaskettua buildingType- ja ikäluokkakohtaista keskimääristä lämmitysmuotojakaumaa, joka on tarkasteltavasta YKR-ruudusta riippumaton.
        
        YKR-ruudun buildingTypeen tilojen lämmitykseen vuoden aikana tarvittu ostoenergia tilat_kwh [kWh/a] on
            
            tilat_kwh = tilat_lammitystarve / tilat_hyotysuhde

        buildingTypeen tilojen lämmityksen tarvitseman ostoenergian kasvihuonekaasupäästöt tilat_co2 [CO2-ekv/a] saadaan kaavalla
        
            tilat_co2 = tilat_kwh * (lmuoto_apu1 * klampo_gco2kwh + lmuoto_apu2 * sahko_gco2kwh + lmuoto_apu3 * tilat_gco2kwh)

        */
        CREATE SCHEMA IF NOT EXISTS functions;
        DROP FUNCTION IF EXISTS functions.CO2_PropertyHeat;
        CREATE OR REPLACE FUNCTION
        functions.CO2_PropertyHeat(
            municipality int,
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            calculationScenario varchar, -- PITKO:n mukainen kehitysskenaario
            floorSpace int, -- Rakennustyypin tietyn ikäluokan kerrosala YKR-ruudussa laskentavuonna. Arvo riippuu laskentavuodesta, rakennuksen tyypistä ja ikäluokasta ja paikallista aineistoa käytettäessä lämmitysmuodosta [m2]
            buildingType varchar, -- buildingType, esim. 'erpien', 'rivita'S
            buildingYear int, -- buildingYear decade tai -vuosi (2017 alkaen)
            method varchar,
            heatSource varchar default null -- Rakennuksen lämmityksessä käytettävä primäärinen energiamuoto 'energiam', mikäli tällainen on lisätty YKR/rakennusdataan
        )
        RETURNS real AS
        $$
        DECLARE -- Joillekin muuttujille on sekä yksittäiset että array-tyyppiset muuttujat, riippuen siitä, onko lähtödatana YKR-dataa (array) vai paikallisesti jalostettua rakennusdataa
            calculationYear integer;
            heating_kwh real; -- Raw heating of spaces without efficiency ratio
            hyotysuhde real; -- Rakennustyypin ikäluokan lämmitysjärjestelmäkohtainen keskimääräinen vuosihyötysuhde tai lämpökerroin. Lukuarvo riippuu rakennuksen ikäluokasta, tyypistä ja lämmitysmuodosta [ei yksikköä].
            hyotysuhde_a real[]; -- Rakennustyypin ikäluokan keskimääräiset vuosihyötysuhteet eri lämmitysjärjestelmille. Lukuarvo riippuu rakennuksen ikäluokasta ja tyypistä [ei yksikköä].
            lammitys_kwh_a real[]; -- Lämmityksen energiankulutus (array)
            lammitys_co2_a real[]; -- Lämmityksen kasvihuonekaasupäästöt [gCO2]
            lammitysosuus real[]; -- Lämmitysmuotojen keskimääräiset osuudet rakennustyypin kerrosalasta tietyssä ikäluokassa laskentavuonna. Lukuarvo riippuu taustaskenaariosta, laskentavuodesta, rakennuksen ikäluokasta ja tyypistä.
            gco2kwh_a real[];
            gco2kwh real; -- Lopulliset ominaispäästökertoimet
            result_gco2 real;
        BEGIN

            /* Returning zero, if grid cell has 0, -1 or NULL built floor area */
            IF floorSpace <= 0 OR floorSpace IS NULL THEN
                RETURN 0;
            /* In other cases continue with the calculation */
            ELSE

                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
                END;

                /* Used when local building register data has been used to derive grid level information incl. heating methods of building */
                IF heatSource IS NOT NULL THEN
                    EXECUTE FORMAT('
                        SELECT %1$I::real
                            FROM built.spaces_efficiency
                            WHERE rakennus_tyyppi = %2$L
                                AND rakv::int = %3$s::int LIMIT 1
                        ', heatSource, buildingType, buildingYear, calculationScenario
                    ) INTO hyotysuhde;
                ELSE
                    /* Used when basing the analysis on pure YKR data */
                    SELECT array[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys]
                        INTO lammitysosuus
                            FROM built.distribution_heating_systems
                            WHERE scenario = calculationScenario
                            AND rakennus_tyyppi = buildingType
                            AND rakv = buildingYear
                            AND year = calculationYear;
                    SELECT array[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys]
                        INTO hyotysuhde_a
                            FROM built.spaces_efficiency
                                WHERE rakennus_tyyppi = buildingType AND 
                                    rakv = buildingYear;
                END IF;

                    /* Energy demand for different building types, per square meter floor space */

                /* Ilmaston lämpenemisen myötä tilojen lämmitystarve pienenee, välillä 2015-2050 noin -17% eli n. 0.5% per vuosi. 
                    Lineaariseksi määritetty kehitys perustuu tutkimukseen:
                    P. Pirinen, H. Simola, S. Nevala, P. Karlsson ja S. Ruuhela, ”Ilmastonmuutos ja lämmitystarveluku paikkatietoarvioina Suomessa,” Ilmastieteen laitos, Helsinki, 2014.
                    ja tässä valittu  aiemman ilmastonmuutosmallinnuksen IPCC:n SRES-kasvihuonekaasuinventaarion A1B-skenaario;
                    Tämä vastaa uusien kasvihuonekaasujen pitoisuuksien kehityskulkuja mallintavien RCP-päästöskenaarioiden optimistisimman RCP4.5- ja pessimistisen RCP8.5-skenaarion välimaastoa.
                */
                EXECUTE FORMAT('
                    WITH spaces AS (
                        -- Rakennustyypin ikäluokkakohtainen kerrosneliömetrin lämmittämiseen vuodessa tarvittu nettolämmitysenergia.
                        -- Kerroin huomioi olevan rakennuskannan energiatehokkuuden kehityksen [kWh/m2/a].
                        SELECT %6$I as kwhm2
                        FROM built.spaces_kwhm2
                            WHERE scenario = %1$L AND rakv = %2$L AND year = %4$L LIMIT 1),
                        heating as (
                            SELECT ((1 - 0.005 * (%4$L::int - 2015)) * multiplier)::real as scaler
                                FROM energy.heating_degree_days dd
                                    WHERE dd.mun::int = %3$L
                        ) SELECT spaces.kwhm2 * heating.scaler * %5$L
                            FROM spaces, heating
                        ', calculationScenario, buildingYear, municipality, calculationYear, floorSpace, buildingType
                ) INTO heating_kwh;

                /* Kaukolämmön ominaispäästökertoimet  */
                /* Emission values for district heating (first finding out the name of the correct district heating table) */
                EXECUTE FORMAT(
                    'WITH district_heating AS (
                        SELECT %3$I as gco2kwh -- Laskentavuonna kulutetun kaukolämmön ominaispäästökerroin [gCO2-ekv/kWh]
                        FROM energy.district_heating heat
                        WHERE heat.year = %1$L
                        AND heat.scenario = %2$L
                        AND heat.mun::int = %4$L
                        ORDER BY %3$I DESC LIMIT 1
                    ), electricity AS (
                        SELECT el.gco2kwh::int AS gco2kwh
                        FROM energy.electricity el
                            WHERE el.year = %1$L
                            AND el.scenario = %2$L
                            AND el.metodi = ''em''
                            AND el.paastolaji = ''tuotanto''
                    ), spaces AS (
                        --  Lämmönlähteiden kasvihuonekaasupäästöjen ominaispäästökertoimet [gCO2-ekv/kWh]
                        SELECT array[kevyt_oljy, kaasu, puu, muu_lammitys] as gco2kwh 
                        FROM energy.spaces_gco2kwh t
                        WHERE t.vuosi = %1$L
                    ) SELECT
                        array[
                            district_heating.gco2kwh, -- kaukolämpö
                            spaces.gco2kwh[1], -- kevyt_oljy
                            spaces.gco2kwh[2], -- kaasu
                            electricity.gco2kwh, -- sahko
                            spaces.gco2kwh[3], -- puu
                            electricity.gco2kwh, -- maalampo
                            spaces.gco2kwh[4] -- muu_lammitys
                        ] FROM district_heating, spaces, electricity
                    ',
                    calculationYear, calculationScenario, method, municipality
                ) INTO gco2kwh_a;

                    /* Lasketaan päästöt tilanteessa, jossa käytetään paikallista rakennusaineistoa */
                    /* Calculating final emission when using local building data */
                    IF heatSource IS NOT NULL THEN
                        -- Lämmityksen energiankulutus (kwh) * gco2 per kwh
                        SELECT heating_kwh / COALESCE(hyotysuhde, 1)::real *
                            CASE WHEN heatSource = 'kaukolampo' THEN gco2kwh_a[1]
                            WHEN heatSource IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN gco2kwh_a[2]
                            WHEN heatSource = 'kaasu' THEN gco2kwh_a[3]
                            WHEN heatSource = 'sahko' THEN gco2kwh_a[4]
                            WHEN heatSource = 'puu' THEN gco2kwh_a[5]
                            WHEN heatSource = 'maalampo' THEN gco2kwh_a[6]
                            WHEN heatSource = 'muu_lammitys' THEN gco2kwh_a[7] ELSE 1 END
                        INTO result_gco2;
                        RETURN result_gco2;
                    ELSE
                    
                    /* Lasketaan päästöt tilanteessa, jossa käytetään YKR-rakennusaineistoa */
                    /* Calculating final emissions when using YKR-based building data */
                        SELECT array(SELECT(heating_kwh / unnest(hyotysuhde_a))) INTO lammitys_kwh_a;
                        SELECT array(SELECT unnest(gco2kwh_a) * unnest(lammitys_kwh_a) * unnest(lammitysosuus)) INTO lammitys_co2_a;

                        /* Palauta CO2-ekvivalenttia */
                        /* Return CO2-equivalents */
                        SELECT SUM(a) FROM unnest(lammitys_co2_a) a INTO result_gco2;
                        RETURN result_gco2;
                    END IF;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Käyttöveden lämmitys | Heating of water

        YKR-ruudun rakennusten vuoden aikana kuluttaman lämpimän käyttöveden lämmitystarve vesi_lammitystarve [kWh/a] on:
            vesi_lammitystarve = rakennus_ala * vesi_kwhm2

        Lämpimän käyttöveden lämmittämiseen tarvittavan ostoenergian tarve vesi_kwh [kWh/a] on:
            vesi_kwh =  vesi_lammitystarve / (tilat_hyotysuhde - 0.05)

        buildingTypeen käyttöveden lämmityksen tarvitseman ostoenergian kasvihuonekaasupäästöt vesi_co2 [CO2-ekv/a] ovat YKR-ruudussa:
            vesi_co2 = vesi_kwh * (lmuoto_apu1 * klampo_gco2kwh + lmuoto_apu2 * sahko_gco2kwh + lmuoto_apu3 * tilat_gco2kwh)
            
        */

        CREATE SCHEMA IF NOT EXISTS functions;
        DROP FUNCTION IF EXISTS functions.CO2_PropertyWater;
        CREATE OR REPLACE FUNCTION
        functions.CO2_PropertyWater(
            municipality int,
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            calculationScenario varchar, -- PITKO:n mukainen kehitysskenaario
            floorSpace int, -- Rakennustyypin ikäluokkakohtainen kerrosala YKR-ruudussa laskentavuonna. Lukuarvo riippuu laskentavuodesta sekä rakennuksen tyypistä ja ikäluokasta [m2]
            buildingType varchar, -- buildingType, esim. 'erpien', 'rivita'
            buildingYear integer, -- buildingYearkymmen tai -vuosi (2017 alkaen)
            method varchar, 
            heatSource varchar default null -- Rakennuksen lämmityksessä käytettävä primäärinen energiamuoto 'energiam', mikäli tällainen on lisätty YKR/rakennusdataan
        )
        RETURNS real AS
        $$
        DECLARE -- Joillekin muuttujille on sekä yksittäiset että array-tyyppiset muuttujat, riippuen siitä, onko lähtödatana YKR-dataa (array) vai paikallisesti jalostettua rakennusdataa
            calculationYear integer; 
            vesi_kwhm2 real; -- Rakennustyypin ikäluokan kerrosalaa kohti vesikuutiometrittäin lasketun lämpimän käyttöveden ominaiskulutuksen [m3/m2/a] ja yhden vesikuution lämmittämiseen tarvittavan energiamäärän 58,3 kWh/m3 tulo. Arvo riippuu laskentaskenaariosta sekä rakennuksen ikäluokasta ja tyypistä [kWh/m2,a].
            hyotysuhde real; -- Rakennustyypin ikäluokan lämmitysjärjestelmäkohtainen keskimääräinen vuosihyötysuhde tai lämpökerroin. Lukuarvo riippuu rakennuksen ikäluokasta, tyypistä ja lämmitysmuodosta [ei yksikköä].
            hyotysuhde_a real[]; -- Rakennustyypin ikäluokan lämmitysjärjestelmäkohtainen keskimääräinen vuosihyötysuhde tai lämpökerroin. Lukuarvo riippuu rakennuksen ikäluokasta, tyypistä ja lämmitysmuodosta [ei yksikköä].
            vesi_kwh real; -- Veden lämmityksen energiankulutus
            vesi_kwh_a real[]; -- Veden lämmityksen energiankulutus
            vesi_co2_a real[]; -- Veden lämmityksen kasvihuonekaasupäästöt [gCO2]
            lammitysosuus real[]; -- Lämmitysmuotojen keskimääräiset osuudet rakennustyypin kerrosalasta tietyssä ikäluokassa laskentavuonna. Lukuarvo riippuu taustaskenaariosta, laskentavuodesta, rakennuksen ikäluokasta ja tyypistä.
            gco2kwh_a real[];
            gco2kwh real; -- Käytettävä ominaispäästökerroin
        BEGIN
            /* Palautetaan nolla, mikäli ruudun kerrosala on 0, -1 tai NULL */
            /* Returning zero, if grid cell has 0, -1 or NULL built floor area */
            IF floorSpace <= 0 OR floorSpace IS NULL
                THEN RETURN 0;
            /* Muussa tapauksessa jatka laskentaan */
            /* In other cases continue with the calculation */
            ELSE

                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
                END;

                /* Käytetään kun on johdettu paikallisesta aineistosta lämmitys/energiamuototiedot ruututasolle */
                /* Used when local building register data has been used to derive grid level information incl. heating methods of building */
                IF heatSource IS NOT NULL THEN
                    EXECUTE FORMAT('
                        SELECT %1$I::real
                            FROM built.spaces_efficiency
                            WHERE rakennus_tyyppi = %2$L
                                AND rakv::int = %3$s::int LIMIT 1
                        ', heatSource, buildingType, buildingYear, calculationScenario
                    ) INTO hyotysuhde;
                ELSE

                /* Käytetään kun käytössä on pelkkää YKR-dataa */
                /* Used when basing the analysis on pure YKR data */
                    SELECT array[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys]
                        INTO lammitysosuus
                            FROM built.distribution_heating_systems
                                WHERE scenario = calculationScenario
                                AND rakennus_tyyppi = buildingType
                                AND rakv = buildingYear
                                AND year = calculationYear;
                    SELECT array[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys]
                        INTO hyotysuhde_a
                            FROM built.spaces_efficiency
                                WHERE rakennus_tyyppi = buildingType
                                AND rakv = buildingYear;
                END IF;

                /* Veden lämmityksen energiankulutus per kerrosneliö */
                /* Water heating power consumption per floor space, square meter */
                SELECT vesi_kwh_m2 INTO vesi_kwhm2
                    FROM built.water_kwhm2 vesi_kwhm2
                    WHERE vesi_kwhm2.scenario = calculationScenario
                    AND vesi_kwhm2.rakennus_tyyppi = buildingType
                    AND vesi_kwhm2.rakv = buildingYear;
            
                /* Kaukolämmön ominaispäästökertoimet  */
                /* Emission values for district heating (first finding out the name of the correct district heating table) */
                EXECUTE FORMAT(
                    'WITH district_heating AS (
                        SELECT %3$I as gco2kwh
                        FROM energy.district_heating heat
                        WHERE heat.year = %1$L
                        AND heat.scenario = %2$L
                        AND heat.mun::int = %4$L::int
                    ), electricity AS (
                        SELECT el.gco2kwh::int AS gco2kwh
                        FROM energy.electricity el
                            WHERE el.year = %1$L
                            AND el.scenario = %2$L
                            AND el.metodi = ''em''
                            AND el.paastolaji = ''tuotanto''
                    ), spaces AS (
                        SELECT array[kevyt_oljy, kaasu, puu, muu_lammitys] as gco2kwh
                        FROM energy.spaces_gco2kwh t
                        WHERE t.vuosi = %1$L LIMIT 1
                    ) SELECT
                        array[
                            district_heating.gco2kwh, -- kaukolampö
                            spaces.gco2kwh[1], -- kevyt_oljy
                            spaces.gco2kwh[2], -- kaasu
                            electricity.gco2kwh, -- sahko
                            spaces.gco2kwh[3], -- puu
                            electricity.gco2kwh, -- maalampo
                            spaces.gco2kwh[4] -- muu_lammitys
                        ]
                        FROM district_heating, spaces, electricity
                    ',
                    calculationYear, calculationScenario, method, municipality
                ) INTO gco2kwh_a;
            

                /* Lasketaan päästöt tilanteessa, jossa käytetään paikallista rakennusaineistoa */
                /* Calculating final emission when using local building data */
                IF heatSource IS NOT NULL THEN
                    SELECT (floorSpace * vesi_kwhm2) / (hyotysuhde::real - 0.05) INTO vesi_kwh;

                        SELECT CASE
                            WHEN heatSource = 'kaukolampo' THEN gco2kwh_a[1]
                            WHEN heatSource IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili') THEN gco2kwh_a[2]
                            WHEN heatSource = 'kaasu' THEN gco2kwh_a[3]
                            WHEN heatSource = 'sahko' THEN gco2kwh_a[4]
                            WHEN heatSource = 'puu' THEN gco2kwh_a[5]
                            WHEN heatSource = 'maalampo' THEN gco2kwh_a[6]
                            WHEN heatSource = 'muu_lammitys' THEN gco2kwh_a[7]
                            END INTO gco2kwh;

                    RETURN vesi_kwh * gco2kwh; -- vesi_co2
                ELSE
                    /* Lasketaan päästöt tilanteessa, jossa käytetään YKR-rakennusaineistoa */
                    /* Calculating final emissions when using YKR-based building data */
                    SELECT array(SELECT(floorSpace * vesi_kwhm2) / (unnest(hyotysuhde_a) - 0.05)) INTO vesi_kwh_a;
                    SELECT array(SELECT unnest(gco2kwh_a) * unnest(vesi_kwh_a) * unnest(lammitysosuus)) INTO vesi_co2_a;

                    /* Palauta CO2-ekvivalentteja */
                    /* Return CO2-equivalents */
                    RETURN SUM(a) FROM unnest(vesi_co2_a) a;
                END IF;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        /* Tavaraliikenne palvelu- ja teollisuuden rakennuksiin
        Goods traffic for service and industry buildings

        Palvelurakennukset luokitellaan kasvihuonekaasupäästölaskelmissa myymälärakennuksiin (myymal_), majoitusliikerakennuksiin (majoit),
        asuntolarakennuksiin (asla), ravintoloihin ja ruokaloihin (ravint), toimistorakennuksiin (tsto), liikenteen rakennuksiin (liiken),
        hoitoalan rakennuksiin (hoito), kookoontumisrakennuksiin (kokoon), opetusrakennuksiin (opetus) ja muihin rakennuksiin (muut).
        Teollisuus- ja varastorakennuksiin sisältyvät teollisuusrakennukset (teoll) ja varastorakennukset (varast).
        */

        /*  Test : 
            SELECT co2_traffic_iwhs_co2('837', 2021::int, 'wem', 3000::int, 'myymal_hyper', array[23, 53, 25, 43, 66, 22, 11, 5, 4])
        */
        DROP FUNCTION IF EXISTS functions.CO2_TrafficIWHS;
        CREATE OR REPLACE FUNCTION
        functions.CO2_TrafficIWHS(
            municipality integer, -- Municipality, for which the values are calculated
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            calculationScenario varchar, -- PITKO:n mukainen kehitysskenaario
            floorSpace integer, -- Rakennusten kerrosala tai lukumäärä (vain teoll ja varast - tapauksissa)
            buildingType varchar -- buildingType | Building type. esim. | e.g. 'erpien', 'rivita'
        )
        RETURNS real AS
        $$
        DECLARE
            calculationYear integer; 
            services varchar[] default ARRAY['myymal_hyper', 'myymal_super', 'myymal_pien', 'myymal_muu', 'myymal', 'majoit', 'asla', 'ravint', 'tsto', 'liiken', 'hoito', 'kokoon', 'opetus', 'muut'];
            gco2_output real;

        BEGIN
            IF  floorSpace <= 0
                OR floorSpace IS NULL
                THEN RETURN 0;
            ELSE

                calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
                END;
            
            /*  Tavarakuljetusten vuosisuorite palv_km [km/a] on laskentavuonna
                    palv_km = rakennus_ala * muunto_ala_tliikenne * palv_suorite * palv_kuljetus_km * arkipaivat
                Paketti- ja kuorma-autojen käyttövoimien suoriteosuuksilla painotettu keskikulutus kmuoto_kwhkm [kWh/km] lasketaan
                    kmuoto_kwhkm = mode_power_distribution * kvoima_kwhkm
                Paketti- ja kuorma-autoilla tehdyn tavaraliikenteen vuosittainen energian käyttö [kWh/a] lasketaan kaavoilla
                    ptv_liikenne_kwh = ptv_km * kmuoto_kwhkm
                Laskentavuoden palvelu- ja teollisuusrakennusten paketti- ja kuorma-autojen tavarakuljetussuoritteiden aiheuttamat kasvihuonekaasupäästöt [CO2-ekv/a] ovat
                    ptv_liikenne_co2 = ptvliikenne_palv_kwh * kmuoto_gco2kwh
            */

            EXECUTE FORMAT(
                'WITH RECURSIVE
                mode_power_distribution AS
                (SELECT kmuoto,
                    array[kvoima_bensiini, kvoima_etanoli, kvoima_diesel, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, kvoima_ev, kvoima_vety, kvoima_muut] as distribution
                    FROM traffic.mode_power_distribution
                        WHERE year = %1$L
                            AND scenario = %2$L
                            AND mun = %3$L
                            AND kmuoto = ANY(%4L)
                ), power_kwhkm as (
                SELECT kmuoto,
                    array[kvoima_bensiini, kvoima_etanoli, kvoima_diesel, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, kvoima_ev, kvoima_vety, kvoima_muut] as kwhkm
                    FROM traffic.power_kwhkm
                        WHERE year = %1$L AND scenario = %2$L AND kmuoto = ANY(%4$L)
                ),
                fossils as (
                    -- Käyttövoimien fossiiliset osuudet [ei yksikköä].
                    SELECT array[share, 1, share, 1, share, share, 1, 1, share] as share
                    FROM traffic.power_fossil_share pfs
                        WHERE pfs.year = %1$L
                        AND pfs.scenario =  %2$L LIMIT 1
                ), electricity_gco2kwh AS (
                    -- Kulutetun sähkön ominaispäästökerroin [gCO2-ekv/kWh]
                    SELECT el.gco2kwh::int AS gco2
                    FROM energy.electricity el
                        WHERE el.year = %1$L
                        AND el.scenario = %2$L
                        AND el.metodi = ''em''
                        AND el.paastolaji = ''tuotanto'' LIMIT 1
                ),
                gco2kwh_matrix as (
                    SELECT 
                    -- Käyttövoimien  kasvihuonekaasujen ominaispäästökerroin käytettyä energiayksikköä kohti [gCO2-ekv/kWh].
                    array( SELECT el.gco2 *
                        -- Dummy, jolla huomioidaan sähkön käyttö sähköautoissa, pistokehybrideissä ja polttokennoautojen vedyn tuotannossa [ei yksikköä].
                        unnest(array[0, 0, 0, 0, 0.5, 0.5, 1, 2.5, 0]) +
                        -- phev_b ja phev_d saavat bensiinin ja dieselin ominaispäästöt = 241 & 237 gco2/kwh
                        -- Etanolin päästöt vuonna 2017 = 49, tuotannon kehityksen myötä n. 0.8 parannus per vuosi
                        unnest(array[241, (49 - (%1$L - 2017) * 0.8), 237, 80, 241, 237, 0, 0, 189]) *
                        unnest(fossils.share) *
                        unnest(array[1, 1, 1, 1, 0.5, 0.5, 0, 0, 1])
                    ) as arr FROM electricity_gco2kwh el, fossils
                ),
                kwh_distribution as (
                    SELECT a.kmuoto,
                        unnest(distribution) * unnest(kwhkm) as kwh,
                        unnest(gco2kwh_matrix.arr) as gco2
                    FROM mode_power_distribution a
                        NATURAL JOIN power_kwhkm b,
                        gco2kwh_matrix
                ),
                distance as 
                -- Apply polynomial regression for estimating size to visits ratio of industry, scale suorite to industry-type weighted average (13.5)
                -- According to Turunen V. TAVARALIIKENTEEN MALLINTAMISESTA HELSINGIN SEUDULLA,
                -- These original traffic estimates create approximately twice the observed amount. Thus half everything.
                (SELECT f.kmuoto, f.%5$I::real *
                    CASE WHEN %8$L = ''industr_performance'' THEN d.%5$I / (CASE WHEN %5$L != ''varast'' THEN 13.5 ELSE 46 END)::real
                        * (0.000000000245131 * %6$L^2 -0.000026867899351 * %6$L + 0.801629386363636)
                        ELSE d.%5$I END
                    * %9$L * 0.01 as km
                FROM traffic.%7$I f
                    LEFT JOIN traffic.%8$I d
                    ON d.kmuoto = f.kmuoto
                    AND d.year = f.year
                    AND d.scenario = f.scenario
                    WHERE f.kmuoto = ANY(%4$L)
                    AND f.year = %1$L
                    AND f.scenario = %2$L)
                SELECT sum(kwh * gco2 * km / 2) * %6$L
                FROM kwh_distribution kwh
                    NATURAL JOIN distance',
            calculationYear, -- 1
            calculationScenario, -- 2
            municipality, -- 3 
            ARRAY['kauto', 'pauto'], -- 4
            buildingType, -- 5
            CASE WHEN floorSpace >= 100000 THEN 100000::real ELSE floorSpace end, -- 6 - kerrosneliömetrit
            CASE WHEN buildingType = ANY(services) THEN 'services_transport_km' ELSE 'industr_transport_km' END, -- 7
            CASE WHEN buildingType = ANY(services) THEN 'service_performance' ELSE 'industr_performance' END, -- 8
            260) INTO gco2_output; -- 9 - Arkipäivien lukumäärä vuodessa (260) [vrk/a].
            
            RETURN gco2_output;

            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        DROP FUNCTION IF EXISTS functions.CO2_TrafficPersonal;

        CREATE OR REPLACE FUNCTION functions.CO2_TrafficPersonal(
            municipality integer,
            pop_or_employ integer, -- Population or number of workplaces
            calculationYears integer[], -- [year based on which emission values are calculated, min, max calculation years]
            mode varchar, -- Mode of transportation
            centdist integer,
            zone bigint,
            calculationScenario varchar,
            traffictype varchar,
            includeLongDistance boolean default false,
            includeBusinessTravel boolean default false
        ) RETURNS real AS $$

        DECLARE
        calculationYear integer; 
        trafficTable varchar;
        km_muutos_bussi real default 0;
        km_muutos_hlauto real default 0;
        kmuoto_hkmvrk real;
        bussi real ;
        hlauto real ;
        raide real ;
        muu real ;
        gco2_km real;
        km real;

        BEGIN 
            IF pop_or_employ <= 0 OR pop_or_employ IS NULL
        THEN RETURN 0;

        else

            calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
            WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
            ELSE calculationYears[1]
            END;

        /* Matkat ja kuormitukset */
        EXECUTE format('SELECT hlt_table FROM traffic.hlt_lookup WHERE mun::int = %L', municipality)
            INTO trafficTable;

        IF zone::bigint NOT IN (1, 2, 6, 10, 837101) THEN
            EXECUTE FORMAT('SELECT bussi
                FROM traffic.hlt_kmchange WHERE zone = CASE
                    WHEN LEFT(%1$L::varchar, 5)::int IN (3, 99931, 99932) THEN 3
                    WHEN LEFT(%1$L::varchar, 5)::int IN (4, 99941, 99942) THEN 4
                    WHEN LEFT(%1$L::varchar, 5)::int IN (5, 99951, 99952) THEN 5
                    ELSE 5 END', zone)
                INTO km_muutos_bussi;

            EXECUTE FORMAT('SELECT hlauto
                FROM traffic.hlt_kmchange WHERE zone = CASE
                    WHEN LEFT(%1$L::varchar, 5)::int IN (3, 99931, 99932) THEN 3
                    WHEN LEFT(%1$L::varchar, 5)::int IN (4, 99941, 99942) THEN 4
                    WHEN LEFT(%1$L::varchar, 5)::int IN (5, 99951, 99952) THEN 5
                    ELSE 5 END', zone)
                INTO km_muutos_hlauto;
        END IF;

        EXECUTE FORMAT('SELECT bussi
        FROM traffic.%1$I
        WHERE zone = CASE
            WHEN LEFT(%2$L::varchar, 4)::int = 9990 THEN 10
                    WHEN LEFT(%2$L::varchar, 3)::int = 999
                        THEN left(right(%2$L, 2), 1)::int
                    WHEN %2$L::bigint = 837101 THEN 6
                    ELSE %2$L::bigint END
        ', trafficTable, zone) INTO bussi;

        EXECUTE FORMAT(
            'SELECT raide
                FROM traffic.%1$I
                WHERE zone = CASE 
                WHEN LEFT(%2$L::varchar, 4)::int = 9990 THEN 10
                    WHEN LEFT(%2$L::varchar, 3)::int = 999
                        THEN left(right(%2$L, 2), 1)::int
                    WHEN %2$L::bigint = 837101 THEN 6
                    ELSE %2$L::bigint END
        ', trafficTable, zone) INTO raide;

        EXECUTE FORMAT('SELECT hlauto
        FROM traffic.%1$I
        WHERE zone = CASE 
            WHEN LEFT(%2$L::varchar, 4)::int = 9990 THEN 10
                    WHEN LEFT(%2$L::varchar, 3)::int = 999
                        THEN left(right(%2$L, 2), 1)::int
                    WHEN %2$L::bigint = 837101 THEN 6
                    ELSE %2$L::bigint END
        ', trafficTable, zone) INTO hlauto;

        EXECUTE FORMAT('SELECT muu
        FROM traffic.%1$I
        WHERE zone = CASE 
            WHEN LEFT(%2$L::varchar, 4)::int = 9990 THEN 10
                    WHEN LEFT(%2$L::varchar, 3)::int = 999
                        THEN left(right(%2$L, 2), 1)::int
                    WHEN %2$L::bigint = 837101 THEN 6
                    ELSE %2$L::bigint END
        ', trafficTable, zone) INTO muu;

        muu := CASE WHEN includeLongDistance THEN muu * 1.6 ELSE 1 END;

        bussi := (
            CASE WHEN centdist > 2 AND centdist < 10
                    AND zone IN (3, 5, 99931, 99932, 99951, 99952, 81, 82, 83, 84, 85, 86, 87)
                    THEN COALESCE(bussi + (centdist - 2) * km_muutos_bussi, 0)
                WHEN centdist > 2
                    AND zone IN (4, 99941, 99942)
                THEN COALESCE(bussi - (centdist - 2) * km_muutos_bussi, 0)
            ELSE bussi END
        ) * CASE WHEN includeLongDistance THEN 3.3 ELSE 1 END; -- HLT-based multipliers for 

        hlauto := (
            CASE WHEN centdist > 2 AND centdist < 10
                    AND zone IN (3, 5, 99931, 99932, 99951, 99952, 81, 82, 83, 84, 85, 86, 87)
                    THEN COALESCE(hlauto + (centdist - 2) * km_muutos_hlauto, 0)
                WHEN centdist > 2 AND zone IN (4, 99941, 99942)
                    THEN COALESCE(hlauto - (centdist - 2) * km_muutos_hlauto, 0)
            ELSE hlauto END
        ) * CASE WHEN includeLongDistance THEN 1.2 ELSE 1 END;

        IF mode = 'raide' THEN
            EXECUTE 'SELECT CASE WHEN LEFT($1::varchar,5)::int IN (99911, 99921, 99931, 99941, 99951, 99961, 99901)
                    THEN $3 + $4 * 0.4 + ($5 * (1.01 ^ ($2 - RIGHT($1::varchar,4)::int + 1)) - $5)
                WHEN LEFT($1::varchar,5)::int IN (99912, 99922, 99932, 99942, 99952, 99962, 99902)
                    THEN $3 + $4 * 0.5 + ($5 * (1.01 ^ ($2 - RIGHT($1::varchar,4)::int + 1)) - $5)
                ELSE $3 END'
                INTO kmuoto_hkmvrk
                USING zone, calculationYear, raide, bussi, hlauto;
        ELSIF mode = 'bussi' THEN
            EXECUTE 'SELECT CASE WHEN LEFT($1::varchar,5)::int IN (99911, 99921, 99931, 99941, 99951, 99961, 99901)
                    THEN $2 * 0.6
                WHEN LEFT($1::varchar,5)::int IN (99912, 99922, 99932, 99942, 99952, 99962, 99902)
                    THEN $2 * 0.5
                ELSE $2 END'
                INTO kmuoto_hkmvrk
                USING zone, bussi;
        ELSIF mode = 'hlauto' THEN
            EXECUTE 'SELECT CASE WHEN LEFT($1::varchar,5)::int IN (99911, 99921, 99931, 99941, 99951, 99961, 99901, 99912, 99922, 99932, 99942, 99952, 99962, 99902) THEN
                $3 * (0.99 ^ ($2 - RIGHT($1::varchar,4)::int + 1))
            ELSE $3 END'
            INTO kmuoto_hkmvrk USING zone,
            calculationYear, hlauto;
        ELSIF mode = 'muu' THEN
            kmuoto_hkmvrk := muu;
        END IF;

        -- mode_power_distribution: Kulkumuotojen käyttövoimajakauma.
        -- power_kwhkm: Energian keskikulutus käyttövoimittain [kWh/km].
        EXECUTE FORMAT(
            'WITH RECURSIVE
            power_distribution AS (
                SELECT
                    array[kvoima_bensiini, kvoima_etanoli, kvoima_diesel, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, kvoima_ev, kvoima_vety, kvoima_muut]
                        as distribution
                    FROM traffic.mode_power_distribution
                        WHERE year = %1$L
                            AND scenario = %2$L::varchar
                            AND mun = %3$L::int
                            AND kmuoto = %4$L::varchar
            ), power_kwhkm as (
                SELECT 
                    array[kvoima_bensiini, kvoima_etanoli, kvoima_diesel, kvoima_kaasu, kvoima_phev_b, kvoima_phev_d, kvoima_ev, kvoima_vety, kvoima_muut] as kwhkm
                    FROM traffic.power_kwhkm
                        WHERE year = %1$L
                            AND scenario = %2$L::varchar
                            AND kmuoto = %4$L::varchar
                LIMIT 1
            ), 
            -- Kasvihuonekaasupäästöjen keskimääräiset ominaispäästökertoimet [gCO2-ekv/kWh] määritellään
            -- käyttövoimien ominaispäästökertoimien suoriteosuuksilla painotettuna keskiarvona huomioiden samalla niiden bio-osuudet.
            fossils as (
                -- Käyttövoimien fossiiliset osuudet [ei yksikköä].
                SELECT array[share, 1, share, 1, share, share, 1, 1, share] as share
                    FROM traffic.power_fossil_share pfs
                        WHERE pfs.year = %1$L
                        AND pfs.scenario =  %2$L LIMIT 1
            ), electricity_gco2kwh AS (
                -- Kulutetun sähkön ominaispäästökerroin [gCO2-ekv/kWh]
                SELECT el.gco2kwh::int AS gco2
                FROM energy.electricity el
                    WHERE el.year::int = %1$s::int
                    AND el.scenario::varchar = %2$L
                    AND el.metodi = ''em''
                    AND el.paastolaji = ''tuotanto'' LIMIT 1
            ), gco2kwh_matrix as (
                SELECT 
                -- Käyttövoimien  kasvihuonekaasujen ominaispäästökerroin käytettyä energiayksikköä kohti [gCO2-ekv/kWh].
                array( SELECT 
                    -- Dummy, jolla huomioidaan sähkön käyttö sähköautoissa, pistokehybrideissä ja polttokennoautojen vedyn tuotannossa [ei yksikköä].
                    el.gco2 * unnest(array[0, 0, 0, 0, 0.5, 0.5, 1, 2.5, 0]) +
                    -- phev_b ja phev_d saavat bensiinin ja dieselin ominaispäästöt = 241 & 237 gco2/kwh
                    -- Etanolin päästöt vuonna 2017 = 49, tuotannon kehityksen myötä n. 0.8 parannus per vuosi
                    unnest(array[241, (49 - (%1$s::int - 2017) * 0.8), 237, 80, 241, 237, 0, 0, 189]) *
                    unnest(fossils.share) *
                    unnest(array[1, 1, 1, 1, 0.5, 0.5, 0, 0, 1])
                ) as arr FROM electricity_gco2kwh el, fossils
            ), co2_km as (
                SELECT
                    unnest(distribution) * unnest(kwhkm) * unnest(gco2kwh_matrix.arr) as gco2km
                FROM power_distribution, power_kwhkm, gco2kwh_matrix
            ) SELECT SUM(gco2km)::real FROM co2_km',
                calculationYear, -- 1
                calculationScenario, -- 2
                municipality, -- 3 
                mode -- 4
            ) INTO gco2_km;
            
        EXECUTE FORMAT('
            WITH RECURSIVE 
                traffic_load as (
                SELECT %4$I as unitload
                    FROM traffic.%8$I
                        WHERE year::int = %1$L::int
                            AND scenario = %2$L
                            AND mun::int = %3$L::int
                        LIMIT 1
            ),  work_share as (
                SELECT %4$I::real as share_w
                FROM traffic.hlt_workshare
                WHERE zone = CASE
                    WHEN LEFT(%5$L::varchar, 4)::int = 9990 THEN 10
                    WHEN LEFT(%5$L::varchar, 3)::int = 999
                        THEN left(right(%5$L, 2), 1)::int
                    WHEN %5$s::bigint = 837101 THEN 6
                    WHEN %5$s::bigint IN (81,82,83,84,85,86,87) THEN 5
                    ELSE %5$s::bigint END LIMIT 1
            ),  distance as (
                SELECT 
                    %7$s::int * %9$L::real * %10$L::real *
                    COALESCE(CASE WHEN %6$L = ''pop'' THEN   (1 - COALESCE(share_w, 0.1) - CASE WHEN %11$L = TRUE THEN 0.05 ELSE 0 END)::real ELSE COALESCE(share_w + CASE WHEN %11$L = TRUE THEN 0.05 ELSE 0 END, 0.1)::real END, 0)
                    / unitload::real
                as km
                    FROM traffic_load, work_share
            ) SELECT SUM(km)::real FROM distance',
                calculationYear, -- 1
                calculationScenario, -- 2
                municipality, -- 3 
                mode, -- 4
                zone, -- 5
                traffictype, -- 6
                COALESCE(pop_or_employ,0), -- 7
                CASE WHEN traffictype = 'pop' THEN 'citizen_traffic_stress' ELSE 'workers_traffic_stress' END, -- 8, asukkaiden tai työssäkäyvien kulkumuotojen keskikuormitukset laskentavuonna [hkm/km].
                kmuoto_hkmvrk, -- 9
                CASE WHEN traffictype = 'pop' THEN 365 ELSE 365 END, -- 10, kuormitus?  Tilastojen mukaan tehollisia työpäiviä keskimäärin noin 228-230 per vuosi ?
                includeBusinessTravel -- 11
            ) INTO km;

        RETURN gco2_km * km;

        END IF;

        END;

        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE SCHEMA IF NOT EXISTS functions;

        DROP FUNCTION IF EXISTS functions.CO2_CalculateEmissions;
        CREATE OR REPLACE FUNCTION
        functions.CO2_CalculateEmissions(
            municipalities integer[],
            aoi regclass, -- Tutkimusalue | area of interest
            includeLongDistance boolean default false,
            includeBusinessTravel boolean default true,
            calculationYears integer[] default array[date_part('year', now()),2017,2050], -- Laskennan viitearvojen year || calculation reference year
            calculationScenario varchar default 'wem', -- PITKO-kehitysskenaario
            method varchar default 'em', -- Päästöallokoinnin laskentamenetelmä
            electricityType varchar default 'tuotanto', -- Sähkön päästölaji
            baseYear integer default NULL, -- Laskennan lähtövuosi
            targetYear integer default NULL, -- Laskennan tavoitevuosi
            plan_areas regclass default NULL, -- Taulu, jossa käyttötarkoitusalueet tai vastaavat
            plan_centers regclass default NULL, -- Taulu, jossa kkreskusverkkotiedot 
            plan_transit regclass default NULL -- Taulu, jossa intensiivinen joukkoliikennejärjestelmä
        )    
        RETURNS TABLE(
            geom geometry(MultiPolygon, 3067),
            xyind varchar(13),
            mun int,
            zone bigint,
            year date,
            floorspace int,
            pop smallint,
            employ smallint,
            tilat_vesi_tco2 real,
            tilat_lammitys_tco2 real,
            tilat_jaahdytys_tco2 real,
            sahko_kiinteistot_tco2 real,
            sahko_kotitaloudet_tco2 real,
            sahko_palv_tco2 real,
            sahko_tv_tco2 real,
            liikenne_as_tco2 real,
            liikenne_tp_tco2 real,
            liikenne_tv_tco2 real,
            liikenne_palv_tco2 real,
            rak_korjaussaneeraus_tco2 real,
            rak_purku_tco2 real,
            rak_uudis_tco2 real,
            sum_yhteensa_tco2 real,
            sum_lammonsaato_tco2 real,
            sum_liikenne_tco2 real,
            sum_sahko_tco2 real,
            sum_rakentaminen_tco2 real
        )
        AS $$
        DECLARE
            calculationYear integer;
            localbuildings boolean;
            refined boolean;
            defaultdemolition boolean;
            initialScenario varchar;
            initialYear integer;
            grams_to_tons real default 0.000001; -- Muuntaa grammat tonneiksi (0.000001) [t/g].
        BEGIN

            /* Jos valitaan 'static'-skenaario, eli huomioidaan laskennassa vain yhdyskuntarakenteen muutos, asetetaan PITKO-skenaarioksi 'wem'.
                Samalla sidotaan laskennan referenssivuodeksi laskennan aloitusyear.
                If the 'static' skenaario is selected, i.e. only changes in the urban structure are taken into account, set the PITKO skenaario to 'wem'.
                At the same time, fix the calculation reference year into current year / baseYear */
            IF calculationScenario = 'static'
                THEN
                    calculationScenario := 'wem';
                    initialScenario := 'static';
            END IF;

            calculationYear := CASE WHEN calculationYears[1] < calculationYears[2] THEN calculationYears[2]
                WHEN calculationYears[1] > calculationYears[3] THEN calculationYears[3]
                ELSE calculationYears[1]
            END;

            IF baseYear IS NULL
                THEN baseYear := calculationYear;
            END IF;

            /* Tarkistetaan, onko käytössä paikallisesti johdettua rakennusdataa, joka sisältää energiamuototiedon */
            /* Checking, whether or not local building data with energy source information is present */
            SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'grid_globals.buildings'::regclass
                AND attname = 'energiam'
                AND NOT attisdropped
            ) INTO localbuildings;

            /* Tarkistetaan, onko käytössä paikallisesti johdettua rakennusdataa, joka sisältää tarkemmat TOL-johdannaiset */
            /* Checking, whether or not local building data with detailed usage source information is present */
            SELECT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'grid_globals.buildings'::regclass
                AND attname = 'myymal_pien_ala'
                AND NOT attisdropped
            ) INTO refined;

            /* Numeeristetaan suunnitelma-aineistoa | 'Numerizing' the given plan data */
            DROP TABLE IF EXISTS grid_temp;
            CREATE TEMP TABLE grid_temp AS
                SELECT * FROM CO2_GridProcessing(municipalities, aoi, calculationYear, baseYear, 1.25, targetYear, plan_areas, plan_centers, plan_transit);
            DROP TABLE IF EXISTS grid;
            ALTER TABLE grid_temp RENAME TO grid;

            --------------------------------------------------------

            IF targetYear IS NOT NULL THEN

                /* Luodaan pohja-aineisto rakennusdatan työstölle */
                /* Building a template for manipulating building data */
                IF calculationYear = baseYear
                    THEN
                        EXECUTE format(
                            'CREATE TEMP TABLE IF NOT EXISTS rak_initial AS
                                SELECT * FROM grid_globals.buildings
                                WHERE rakv::int != 0
                                    AND xyind::varchar IN
                                        (SELECT grid.xyind::varchar FROM grid)
                                    AND rakv::int < %L',
                        calculationYear);
                    ELSE 
                        ALTER TABLE grid2 RENAME to rak_initial;
                END IF;

                SELECT CASE WHEN k_poistuma > 999998 AND k_poistuma < 1000000 THEN TRUE ELSE FALSE END FROM grid LIMIT 1 INTO defaultdemolition;

                /* Luodaan väliaikainen taulu rakennusten purkamisen päästölaskentaa varten
                Creating a temporary table for emission calculations of demolishing buildings
                Default demolishing rate: 0.15% annually of existing building stock.
                Huuhka, S. & Lahdensivu J. Statistical and geographical study on demolish buildings. Building research and information vol 44:1, 73-96. */
                IF defaultdemolition = TRUE THEN
                CREATE TEMP TABLE poistuma_alat AS 
                    SELECT rak_initial.xyind, 
                        0.0015 * SUM(rakyht_ala)::real rakyht,
                        0.0015 * SUM(erpien_ala)::real erpien,
                        0.0015 * SUM(rivita_ala)::real rivita,
                        0.0015 * SUM(askert_ala)::real askert,
                        0.0015 * SUM(liike_ala)::real liike,
                        0.0015 * SUM(tsto_ala)::real tsto,
                        0.0015 * SUM(liiken_ala)::real liiken,
                        0.0015 * SUM(hoito_ala)::real hoito,
                        0.0015 * SUM(kokoon_ala)::real kokoon,
                        0.0015 * SUM(opetus_ala)::real opetus,
                        0.0015 * SUM(teoll_ala)::real teoll,
                        0.0015 * SUM(varast_ala)::real varast,
                        0.0015 * SUM(muut_ala)::real muut
                    FROM rak_initial
                    WHERE rakyht_ala > 0
                    GROUP BY rak_initial.xyind;

                ELSE

                    CREATE TEMP TABLE poistuma_alat AS 
                    WITH poistuma AS (
                        SELECT grid.xyind::varchar, SUM(k_poistuma) AS poistuma FROM grid GROUP BY grid.xyind
                    ),
                    buildings AS (
                        SELECT rak_initial.xyind, 
                            SUM(rakyht_ala) rakyht_ala,
                            SUM(erpien_ala) erpien_ala,
                            SUM(rivita_ala) rivita_ala,
                            SUM(askert_ala) askert_ala,
                            SUM(liike_ala) liike_ala,
                            SUM(tsto_ala) tsto_ala,
                            SUM(liiken_ala) liiken_ala,
                            SUM(hoito_ala) hoito_ala,
                            SUM(kokoon_ala) kokoon_ala,
                            SUM(opetus_ala) opetus_ala,
                            SUM(teoll_ala) teoll_ala,
                            SUM(varast_ala) varast_ala,
                            SUM(muut_ala) muut_ala
                        FROM rak_initial GROUP BY rak_initial.xyind
                    )
                    SELECT poistuma.xyind,
                        COALESCE(poistuma * (erpien_ala::real / NULLIF(rakyht_ala::real,0)),0) erpien,
                        COALESCE(poistuma * (rivita_ala::real / NULLIF(rakyht_ala::real,0)),0) rivita,
                        COALESCE(poistuma * (askert_ala::real / NULLIF(rakyht_ala::real,0)),0) askert,
                        COALESCE(poistuma * (liike_ala::real / NULLIF(rakyht_ala::real,0)),0) liike,
                        COALESCE(poistuma * (tsto_ala::real / NULLIF(rakyht_ala::real,0)),0) tsto,
                        COALESCE(poistuma * (liiken_ala::real / NULLIF(rakyht_ala::real,0)),0) liiken,
                        COALESCE(poistuma * (hoito_ala::real / NULLIF(rakyht_ala::real,0)),0) hoito,
                        COALESCE(poistuma * (kokoon_ala::real / NULLIF(rakyht_ala::real,0)),0) kokoon,
                        COALESCE(poistuma * (opetus_ala::real / NULLIF(rakyht_ala::real,0)),0) opetus,
                        COALESCE(poistuma * (teoll_ala::real / NULLIF(rakyht_ala::real,0)),0) teoll,
                        COALESCE(poistuma * (varast_ala::real / NULLIF(rakyht_ala::real,0)),0) varast,
                        COALESCE(poistuma * (muut_ala::real / NULLIF(rakyht_ala::real,0)),0) muut
                    FROM poistuma
                        LEFT JOIN buildings ON buildings.xyind = poistuma.xyind
                    WHERE poistuma > 0;
                END IF;

                /* Kyselyt: Puretaan rakennukset datasta ja rakennetaan uusia */
                /* Valitaan ajettava kysely sen perusteella, millaista rakennusdataa on käytössä */
                /* Queries: Demolishing and buildings buildings from the building data */
                /* Choose correct query depending on the type of building data in use */
                RAISE NOTICE 'Updating building data';
                IF localbuildings = true THEN
                    IF refined = true THEN 
                        EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS grid2 AS SELECT xyind::varchar, rakv::int, energiam, rakyht_ala :: int, asuin_ala :: int, erpien_ala :: int, rivita_ala :: int, askert_ala :: int, liike_ala :: int, myymal_ala :: int, myymal_pien_ala :: int, myymal_super_ala :: int, myymal_hyper_ala :: int, myymal_muu_ala :: int, majoit_ala :: int, asla_ala :: int, ravint_ala :: int, tsto_ala :: int, liiken_ala :: int, hoito_ala :: int, kokoon_ala :: int, opetus_ala :: int, teoll_ala :: int, teoll_elint_ala :: int, teoll_tekst_ala :: int, teoll_puu_ala :: int, teoll_paper_ala :: int, teoll_miner_ala :: int, teoll_kemia_ala :: int, teoll_kone_ala :: int, teoll_mjalos_ala :: int, teoll_metal_ala :: int, teoll_vesi_ala :: int, teoll_energ_ala :: int, teoll_yhdysk_ala :: int, teoll_kaivos_ala :: int, teoll_muu_ala :: int, varast_ala :: int, muut_ala :: int FROM (SELECT * FROM CO2_UpdateBuildingsRefined(''rak_initial'', ''grid'', %L, %L, %L, %L)) updatedbuildings', calculationYears, baseYear, targetYear, calculationScenario);
                    ELSE 
                        EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS grid2 AS SELECT xyind::varchar, rakv::int, energiam, rakyht_ala :: int, asuin_ala :: int, erpien_ala :: int, rivita_ala :: int, askert_ala :: int, liike_ala :: int, myymal_ala :: int, majoit_ala :: int, asla_ala :: int, ravint_ala :: int, tsto_ala :: int, liiken_ala :: int, hoito_ala :: int, kokoon_ala :: int, opetus_ala :: int, teoll_ala :: int, varast_ala :: int, muut_ala :: int FROM (SELECT * FROM CO2_UpdateBuildingsLocal(''rak_initial'', ''grid'', %L, %L, %L, %L)) updatedbuildings', calculationYears, baseYear, targetYear, calculationScenario);
                    END IF;
                    CREATE INDEX ON grid2 (rakv, energiam);
                ELSE
                    EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS grid2 AS SELECT xyind::varchar, rakv::int, rakyht_ala :: int, asuin_ala :: int, erpien_ala :: int, rivita_ala :: int, askert_ala :: int, liike_ala :: int, myymal_ala :: int, majoit_ala :: int, asla_ala :: int, ravint_ala :: int, tsto_ala :: int, liiken_ala :: int, hoito_ala :: int, kokoon_ala :: int, opetus_ala :: int, teoll_ala :: int, varast_ala :: int, muut_ala :: int FROM (SELECT * FROM CO2_UpdateBuildings(''rak_initial'', ''grid'', %L)) updatedbuildings', year);
                    CREATE INDEX ON grid2 (rakv);        
                END IF;
                DROP TABLE IF EXISTS rak_initial;

            ELSE

                /* Valitaan rakennustietojen väliaikaisen taulun generointikysely ajettavaksi sen perusteella, millaista rakennusdataa on käytössä */
                /* Choose correct query for creating a temporary building data table depending on the type of building data in use */
                IF localbuildings = true THEN
                    IF refined = true THEN

                        CREATE TEMP TABLE IF NOT EXISTS
                            grid2 AS SELECT
                            b.xyind::varchar,
                            rakv::int,
                            energiam::varchar,
                            rakyht_ala::int,
                            asuin_ala :: int,
                            erpien_ala :: int,
                            rivita_ala :: int,
                            askert_ala :: int,
                            liike_ala :: int,
                            myymal_ala :: int,
                            myymal_pien_ala :: int,
                            myymal_super_ala :: int,
                            myymal_hyper_ala :: int,
                            myymal_muu_ala :: int,
                            majoit_ala :: int,
                            asla_ala :: int,
                            ravint_ala :: int,
                            tsto_ala :: int,
                            liiken_ala :: int,
                            hoito_ala :: int,
                            kokoon_ala :: int,
                            opetus_ala :: int,
                            teoll_ala :: int,
                            teoll_elint_ala :: int,
                            teoll_tekst_ala :: int,
                            teoll_puu_ala :: int,
                            teoll_paper_ala :: int,
                            teoll_miner_ala :: int,
                            teoll_kemia_ala :: int,
                            teoll_kone_ala :: int,
                            teoll_mjalos_ala :: int,
                            teoll_metal_ala :: int,
                            teoll_vesi_ala :: int,
                            teoll_energ_ala :: int,
                            teoll_yhdysk_ala :: int,
                            teoll_kaivos_ala :: int,
                            teoll_muu_ala :: int,
                            varast_ala :: int,
                            muut_ala :: int
                            FROM grid_globals.buildings b
                                WHERE rakv::int != 0
                                AND b.xyind::varchar IN
                                    (SELECT grid.xyind::varchar FROM grid);
                    ELSE 
                        CREATE TEMP TABLE IF NOT EXISTS grid2 AS SELECT b.xyind::varchar, rakv::int, energiam, rakyht_ala :: int, asuin_ala :: int, erpien_ala :: int, rivita_ala :: int, askert_ala :: int, liike_ala :: int, myymal_ala :: int, majoit_ala :: int, asla_ala :: int, ravint_ala :: int, tsto_ala :: int, liiken_ala :: int, hoito_ala :: int, kokoon_ala :: int, opetus_ala :: int, teoll_ala :: int, varast_ala :: int, muut_ala :: int FROM grid_globals.buildings b WHERE rakv::int != 0 AND b.xyind IN (SELECT grid.xyind FROM grid);
                    END IF;
                    CREATE INDEX ON grid2 (rakv, energiam);
                ELSE
                        CREATE TEMP TABLE IF NOT EXISTS grid2 AS SELECT b.xyind::varchar, rakv::int, rakyht_ala :: int, asuin_ala :: int, erpien_ala :: int, rivita_ala :: int, askert_ala :: int, liike_ala :: int, myymal_ala :: int, majoit_ala :: int, asla_ala :: int, ravint_ala :: int, tsto_ala :: int, liiken_ala :: int, hoito_ala :: int, kokoon_ala :: int, opetus_ala :: int, teoll_ala :: int, varast_ala :: int, muut_ala :: int FROM grid_globals.buildings b WHERE rakv::int != 0 AND b.xyind IN (SELECT grid.xyind FROM grid);
                    CREATE INDEX ON grid2 (rakv); -- update?
                END IF;

            END IF;

            /* Luodaan väliaikainen taulu laskennan tuloksille */
            /* Creating temporary table for analysis results */
            DROP TABLE IF EXISTS results;
            CREATE TEMP TABLE results AS SELECT
                g.geom::geometry(MultiPolygon, 3067),
                g.xyind::varchar(13),
                g.mun::int,
                g.zone::bigint,
                NULL::date as year,
                0::int floorspace,
                COALESCE(g.pop, 0)::smallint pop,
                COALESCE(g.employ, 0)::smallint employ,
                0::real tilat_vesi_tco2,
                0::real tilat_lammitys_tco2,
                0::real tilat_jaahdytys_tco2,
                0::real sahko_kiinteistot_tco2,
                0::real sahko_kotitaloudet_tco2,
                0::real sahko_palv_tco2,
                0::real sahko_tv_tco2,
                0::real liikenne_as_tco2,
                0::real liikenne_tp_tco2,
                0::real liikenne_tv_tco2,
                0::real liikenne_palv_tco2,
                0::real rak_korjaussaneeraus_tco2,
                0::real rak_purku_tco2,
                0::real rak_uudis_tco2,
                0::real sum_yhteensa_tco2,
                0::real sum_lammonsaato_tco2,
                0::real sum_liikenne_tco2,
                0::real sum_sahko_tco2,
                0::real sum_rakentaminen_tco2
            FROM grid g
                WHERE (COALESCE(g.pop,0) > 0 OR COALESCE(g.employ,0) > 0 )
                    OR g.xyind::varchar IN (SELECT DISTINCT ON (grid2.xyind) grid2.xyind::varchar FROM grid2);

            /* Kun käytetään static-skenaariota tulevaisuuslaskennassa, aseta laskenta lähtövuoden referenssitasolle */
            /* When using a 'static' scenario in the future scenario calculation, set the calculation reference year to baseYear */
            IF initialScenario = 'static'
                AND targetYear IS NOT NULL THEN
                initialYear := calculationYear;
                calculationYear := baseYear;
                calculationYears[1] := baseYear;
            END IF;

            ALTER TABLE grid2 ADD COLUMN IF NOT EXISTS mun int;
            UPDATE grid2 g2
                SET mun = g.mun
                FROM grid g
                WHERE g.xyind::varchar = g2.xyind::varchar;
            
            /* Täytetään tulostaulukko laskennan tuloksilla */
            /* Fill results table with calculations */

            IF localbuildings = TRUE THEN

                UPDATE results SET 
                    tilat_vesi_tco2 = COALESCE(buildings.property_water_gco2, 0) * grams_to_tons,
                    tilat_lammitys_tco2 = COALESCE(buildings.property_heat_gco2, 0) * grams_to_tons
                FROM
                    (SELECT DISTINCT ON (g2.xyind) g2.xyind,
                    /* Käyttöveden lämmitys | Heating of water */
                    SUM((SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, erpien_ala, 'erpien', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, rivita_ala, 'rivita', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, askert_ala, 'askert', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, liike_ala, 'liike', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, tsto_ala, 'tsto', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, liiken_ala, 'liiken', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, hoito_ala, 'hoito', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, kokoon_ala, 'kokoon', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, opetus_ala, 'opetus', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, teoll_ala, 'teoll', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, varast_ala, 'varast', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, muut_ala, 'muut', g2.rakv, method, g2.energiam)))
                    AS property_water_gco2,
                    /* Rakennusten lämmitys | Heating of buildings */
                    SUM((SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, erpien_ala, 'erpien', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, rivita_ala, 'rivita', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, askert_ala, 'askert', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, liike_ala, 'liike', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, tsto_ala, 'tsto', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, liiken_ala, 'liiken', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, hoito_ala, 'hoito', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, kokoon_ala, 'kokoon', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, opetus_ala, 'opetus', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, teoll_ala, 'teoll', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, varast_ala, 'varast', g2.rakv, method, g2.energiam)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, muut_ala, 'muut', g2.rakv, method, g2.energiam)))
                    AS property_heat_gco2
                    FROM grid2 g2
                        GROUP BY g2.xyind) buildings
                    WHERE buildings.xyind::varchar = results.xyind::varchar;

            ELSE

                UPDATE results SET 
                    tilat_vesi_tco2 = COALESCE(buildings.property_water_gco2, 0) * grams_to_tons,
                    tilat_lammitys_tco2 = COALESCE(buildings.property_heat_gco2, 0) * grams_to_tons
                FROM
                    (SELECT DISTINCT ON (g2.xyind) g2.xyind,
                    /* Käyttöveden lämmitys | Heating of water */
                    SUM((SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, erpien_ala, 'erpien', g2.rakv, method)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, rivita_ala, 'rivita', g2.rakv, method)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, askert_ala, 'askert', g2.rakv, method)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, liike_ala, 'liike', g2.rakv, method)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, tsto_ala, 'tsto', g2.rakv, method)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, liiken_ala, 'liiken', g2.rakv, method)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, hoito_ala, 'hoito', g2.rakv, method)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, kokoon_ala, 'kokoon', g2.rakv, method)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, opetus_ala, 'opetus', g2.rakv, method)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, teoll_ala, 'teoll', g2.rakv, method)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, varast_ala, 'varast', g2.rakv, method)) +
                        (SELECT CO2_PropertyWater(g2.mun, calculationYears, calculationScenario, muut_ala, 'muut', g2.rakv, method)))
                    AS property_water_gco2,
                    /* Rakennusten lämmitys | Heating of buildings */
                    SUM((SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, erpien_ala, 'erpien', g2.rakv, method)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, rivita_ala, 'rivita', g2.rakv, method)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, askert_ala, 'askert', g2.rakv, method)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, liike_ala, 'liike', g2.rakv, method)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, tsto_ala, 'tsto', g2.rakv, method)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, liiken_ala, 'liiken', g2.rakv, method)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, hoito_ala, 'hoito', g2.rakv, method)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, kokoon_ala, 'kokoon', g2.rakv, method)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, opetus_ala, 'opetus', g2.rakv, method)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, teoll_ala, 'teoll', g2.rakv, method)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, varast_ala, 'varast', g2.rakv, method)) +
                        (SELECT CO2_PropertyHeat(g2.mun, calculationYears, calculationScenario, muut_ala, 'muut', g2.rakv, method)))
                    AS property_heat_gco2
                    FROM grid2 g2
                    GROUP BY g2.xyind) buildings
                    WHERE buildings.xyind::varchar = results.xyind::varchar;
            END IF;

            UPDATE results SET 
                tilat_jaahdytys_tco2 = COALESCE(buildings.property_cooling_gco2 * grams_to_tons, 0),
                sahko_kiinteistot_tco2 = COALESCE(buildings.sahko_kiinteistot_co2 * grams_to_tons, 0),
                sahko_kotitaloudet_tco2 = COALESCE(buildings.sahko_kotitaloudet_co2 * grams_to_tons, 0),
                rak_korjaussaneeraus_tco2 = COALESCE(buildings.rak_korjaussaneeraus_co2 * grams_to_tons, 0)
            FROM
                (SELECT DISTINCT ON (g2.xyind) g2.xyind,
                /* Rakennusten jäähdytys | Cooling of buildings */
                SUM((SELECT CO2_PropertyCooling(calculationYears, calculationScenario, erpien_ala, 'erpien', g2.rakv)) +
                    (SELECT CO2_PropertyCooling(calculationYears, calculationScenario, rivita_ala, 'rivita', g2.rakv)) +
                    (SELECT CO2_PropertyCooling(calculationYears, calculationScenario, askert_ala, 'askert', g2.rakv)) +
                    (SELECT CO2_PropertyCooling(calculationYears, calculationScenario, liike_ala, 'liike', g2.rakv)) +
                    (SELECT CO2_PropertyCooling(calculationYears, calculationScenario, tsto_ala, 'tsto', g2.rakv)) +
                    (SELECT CO2_PropertyCooling(calculationYears, calculationScenario, liiken_ala, 'liiken', g2.rakv)) +
                    (SELECT CO2_PropertyCooling(calculationYears, calculationScenario, hoito_ala, 'hoito', g2.rakv)) +
                    (SELECT CO2_PropertyCooling(calculationYears, calculationScenario, kokoon_ala, 'kokoon', g2.rakv)) +
                    (SELECT CO2_PropertyCooling(calculationYears, calculationScenario, opetus_ala, 'opetus', g2.rakv)) +
                    (SELECT CO2_PropertyCooling(calculationYears, calculationScenario, teoll_ala, 'teoll', g2.rakv)) +
                    (SELECT CO2_PropertyCooling(calculationYears, calculationScenario, varast_ala, 'varast', g2.rakv)) +
                    (SELECT CO2_PropertyCooling(calculationYears, calculationScenario, muut_ala, 'muut', g2.rakv)))
                AS property_cooling_gco2,
                /* Kiinteistösähkö | Electricity consumption of property technology */
                SUM((SELECT CO2_ElectricityProperty(calculationYears, calculationScenario, erpien_ala, 'erpien', g2.rakv)) +
                    (SELECT CO2_ElectricityProperty(calculationYears, calculationScenario, rivita_ala, 'rivita', g2.rakv)) +
                    (SELECT CO2_ElectricityProperty(calculationYears, calculationScenario, askert_ala, 'askert', g2.rakv)) +
                    (SELECT CO2_ElectricityProperty(calculationYears, calculationScenario, liike_ala,  'liike', g2.rakv)) +
                    (SELECT CO2_ElectricityProperty(calculationYears, calculationScenario, tsto_ala, 'tsto', g2.rakv)) +
                    (SELECT CO2_ElectricityProperty(calculationYears, calculationScenario, liiken_ala, 'liiken', g2.rakv)) +
                    (SELECT CO2_ElectricityProperty(calculationYears, calculationScenario, hoito_ala, 'hoito', g2.rakv)) +
                    (SELECT CO2_ElectricityProperty(calculationYears, calculationScenario, kokoon_ala, 'kokoon', g2.rakv)) +
                    (SELECT CO2_ElectricityProperty(calculationYears, calculationScenario, opetus_ala, 'opetus', g2.rakv)) +
                    (SELECT CO2_ElectricityProperty(calculationYears, calculationScenario, teoll_ala, 'teoll', g2.rakv)) +
                    (SELECT CO2_ElectricityProperty(calculationYears, calculationScenario, varast_ala, 'varast', g2.rakv)) +
                    (SELECT CO2_ElectricityProperty(calculationYears, calculationScenario, muut_ala, 'muut', g2.rakv)))
                AS sahko_kiinteistot_co2,
                /* Kotitalouksien sähkönkulutus | Energy consumption of households */
                SUM((SELECT CO2_ElectricityHousehold(g2.mun, calculationYears, calculationScenario, erpien_ala, 'erpien')) +
                    (SELECT CO2_ElectricityHousehold(g2.mun, calculationYears, calculationScenario, rivita_ala, 'rivita')) +
                    (SELECT CO2_ElectricityHousehold(g2.mun, calculationYears, calculationScenario, askert_ala, 'askert')))
                AS sahko_kotitaloudet_co2,
                /* Korjausrakentaminen ja saneeraus | Renovations and large-scale overhauls of buildings */
                SUM((SELECT CO2_BuildRenovate(erpien_ala, calculationYears, 'erpien', g2.rakv, calculationScenario)) +
                    (SELECT CO2_BuildRenovate(rivita_ala, calculationYears, 'rivita', g2.rakv, calculationScenario)) +
                    (SELECT CO2_BuildRenovate(askert_ala, calculationYears, 'askert', g2.rakv, calculationScenario)) +
                    (SELECT CO2_BuildRenovate(liike_ala, calculationYears, 'liike', g2.rakv, calculationScenario)) +
                    (SELECT CO2_BuildRenovate(tsto_ala, calculationYears, 'tsto', g2.rakv, calculationScenario)) +
                    (SELECT CO2_BuildRenovate(liiken_ala, calculationYears, 'liiken', g2.rakv, calculationScenario)) +
                    (SELECT CO2_BuildRenovate(hoito_ala, calculationYears, 'hoito', g2.rakv, calculationScenario)) +
                    (SELECT CO2_BuildRenovate(kokoon_ala, calculationYears, 'kokoon', g2.rakv, calculationScenario)) +
                    (SELECT CO2_BuildRenovate(opetus_ala, calculationYears, 'opetus', g2.rakv, calculationScenario)) +
                    (SELECT CO2_BuildRenovate(teoll_ala, calculationYears, 'teoll', g2.rakv, calculationScenario)) +
                    (SELECT CO2_BuildRenovate(varast_ala, calculationYears, 'varast', g2.rakv, calculationScenario)) +
                    (SELECT CO2_BuildRenovate(muut_ala, calculationYears, 'muut', g2.rakv, calculationScenario)))
                AS rak_korjaussaneeraus_co2
                    FROM grid2 g2
                        GROUP BY g2.xyind
                ) buildings
                    WHERE buildings.xyind::varchar = results.xyind::varchar;
        
            IF refined = FALSE THEN

                UPDATE results
                SET sahko_palv_tco2 = COALESCE(buildings.sahko_palv_co2 * grams_to_tons, 0),
                    sahko_tv_tco2 = COALESCE(buildings.sahko_tv_co2 * grams_to_tons, 0),
                    liikenne_tv_tco2 = COALESCE(buildings.liikenne_tv_co2 * grams_to_tons, 0),
                    liikenne_palv_tco2 = COALESCE(buildings.liikenne_palv_co2 * grams_to_tons, 0)
                FROM
                    (SELECT DISTINCT ON (g2.xyind) g2.xyind,
                    /* Palveluiden sähkönkulutus | Electricity consumption of services */
                    SUM((SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, liike_ala, 'liike')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, tsto_ala, 'tsto')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, liiken_ala, 'liiken')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, hoito_ala, 'hoito')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, kokoon_ala, 'kokoon')) +	
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, opetus_ala, 'opetus')))
                    AS sahko_palv_co2,
                    /* Teollisuus ja varastot, sähkönkulutus | Electricity consumption of industry and warehouses */
                    SUM((SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_ala, 'teoll')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, varast_ala, 'varast')))
                    AS sahko_tv_co2,
                    /* Teollisuus- ja varastoliikenne | Industry and logistics traffic */
                    SUM((SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_ala, 'teoll')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, varast_ala, 'varast')))
                    AS liikenne_tv_co2,
                    /* Palveluliikenne | Service traffic */
                    SUM((SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, myymal_ala, 'myymal')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, asla_ala, 'asla')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, ravint_ala, 'ravint')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, tsto_ala, 'tsto')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, liiken_ala, 'liiken')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, hoito_ala, 'hoito')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, kokoon_ala, 'kokoon')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, opetus_ala, 'opetus')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, muut_ala, 'muut')))
                    AS liikenne_palv_co2
                    FROM grid2 g2
                    GROUP BY g2.xyind) buildings
                WHERE buildings.xyind = results.xyind;
                
            ELSE 

                UPDATE results
                SET sahko_palv_tco2 = COALESCE(buildings.sahko_palv_co2 * grams_to_tons, 0),
                    sahko_tv_tco2 = COALESCE(buildings.sahko_tv_co2 * grams_to_tons, 0),
                    liikenne_tv_tco2 = COALESCE(buildings.liikenne_tv_co2 * grams_to_tons, 0),
                    liikenne_palv_tco2 = COALESCE(buildings.liikenne_palv_co2 * grams_to_tons, 0)
                FROM
                    (SELECT DISTINCT ON (g2.xyind) g2.xyind,
                    /* Palveluiden sähkönkulutus | Electricity consumption of services */
                    SUM((SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, myymal_hyper_ala, 'myymal_hyper')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, myymal_super_ala, 'myymal_super')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, myymal_pien_ala, 'myymal_pien')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, myymal_muu_ala, 'myymal_muu')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, majoit_ala, 'majoit')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, asla_ala, 'asla')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, ravint_ala, 'ravint')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, tsto_ala, 'tsto')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, liiken_ala, 'liiken')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, hoito_ala, 'hoito')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, kokoon_ala, 'kokoon')) +	
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, opetus_ala, 'opetus')))
                    AS sahko_palv_co2,
                    /* Teollisuus ja varastot, sähkönkulutus | Electricity consumption of industry and warehouses */
                    SUM((SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_kaivos_ala, 'teoll_kaivos')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_elint_ala, 'teoll_elint')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_tekst_ala, 'teoll_tekst')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_puu_ala, 'teoll_puu')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_paper_ala, 'teoll_paper')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_kemia_ala, 'teoll_kemia')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_miner_ala, 'teoll_miner')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_mjalos_ala, 'teoll_mjalos')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_metal_ala, 'teoll_metal')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_kone_ala, 'teoll_kone')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_muu_ala, 'teoll_muu')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_energ_ala, 'teoll_energ')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_vesi_ala, 'teoll_vesi')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, teoll_yhdysk_ala, 'teoll_yhdysk')) +
                        (SELECT CO2_ElectricityIWHS(calculationYears, calculationScenario, varast_ala, 'varast')))
                    AS sahko_tv_co2,
                    /* Teollisuus- ja varastoliikenne | Industry and logistics traffic */
                    SUM((SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_kaivos_ala, 'teoll_kaivos')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_elint_ala, 'teoll_elint')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_tekst_ala, 'teoll_tekst')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_puu_ala, 'teoll_puu')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_paper_ala, 'teoll_paper')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_kemia_ala, 'teoll_kemia')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_miner_ala, 'teoll_miner')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_mjalos_ala, 'teoll_mjalos')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_metal_ala, 'teoll_metal')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_kone_ala, 'teoll_kone')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_muu_ala, 'teoll_muu')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_energ_ala, 'teoll_energ')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_vesi_ala, 'teoll_vesi')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, teoll_yhdysk_ala, 'teoll_yhdysk')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, varast_ala, 'varast')))
                    AS liikenne_tv_co2,
                    /* Palveluliikenne | Service traffic */
                    SUM((SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, myymal_hyper_ala, 'myymal_hyper')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, myymal_super_ala, 'myymal_super')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, myymal_pien_ala, 'myymal_pien')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, myymal_muu_ala, 'myymal_muu')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, majoit_ala, 'majoit')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, asla_ala, 'asla')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, ravint_ala, 'ravint')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, tsto_ala, 'tsto')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, liiken_ala, 'liiken')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, hoito_ala, 'hoito')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, kokoon_ala, 'kokoon')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, opetus_ala, 'opetus')) +
                        (SELECT CO2_TrafficIWHS(g2.mun, calculationYears, calculationScenario, muut_ala, 'muut')))
                    AS liikenne_palv_co2
                        FROM grid2 g2
                        GROUP BY g2.xyind
                    ) buildings
                WHERE buildings.xyind = results.xyind;
            END IF;

            IF targetYear IS NOT NULL THEN
                UPDATE results SET
                    rak_uudis_tco2 = COALESCE(buildings.rak_uudis_co2 * grams_to_tons, 0)
                FROM
                    (SELECT DISTINCT ON (grid2.xyind) grid2.xyind,
                    SUM((SELECT CO2_BuildConstruct(erpien_ala, calculationYears, 'erpien', calculationScenario)) +
                        (SELECT CO2_BuildConstruct(rivita_ala, calculationYears, 'rivita', calculationScenario)) +
                        (SELECT CO2_BuildConstruct(askert_ala, calculationYears, 'askert', calculationScenario)) +
                        (SELECT CO2_BuildConstruct(liike_ala, calculationYears, 'liike', calculationScenario)) +
                        (SELECT CO2_BuildConstruct(tsto_ala, calculationYears, 'tsto', calculationScenario)) +
                        (SELECT CO2_BuildConstruct(liiken_ala, calculationYears, 'liiken', calculationScenario)) +
                        (SELECT CO2_BuildConstruct(hoito_ala, calculationYears, 'hoito', calculationScenario)) +
                        (SELECT CO2_BuildConstruct(kokoon_ala, calculationYears, 'kokoon', calculationScenario)) +
                        (SELECT CO2_BuildConstruct(opetus_ala, calculationYears, 'opetus', calculationScenario)) +
                        (SELECT CO2_BuildConstruct(teoll_ala, calculationYears, 'teoll', calculationScenario)) +
                        (SELECT CO2_BuildConstruct(varast_ala, calculationYears, 'varast', calculationScenario)) +
                        (SELECT CO2_BuildConstruct(muut_ala, calculationYears, 'muut', calculationScenario))
                    ) AS rak_uudis_co2
                        FROM grid2  
                            WHERE grid2.rakv = calculationYear
                            GROUP BY grid2.xyind
                    ) buildings
                            WHERE buildings.xyind = results.xyind;

                /* Lasketaan rakennusten purkamisen päästöt */
                /* Calculating emissions for demolishing buildings */
                UPDATE results SET rak_purku_tco2 = COALESCE(poistot.rak_purku_co2 * grams_to_tons, 0)
                    FROM (SELECT p.xyind,
                        SUM((SELECT CO2_BuildDemolish(p.erpien::real, calculationYears, 'erpien', calculationScenario)) +
                            (SELECT CO2_BuildDemolish(p.rivita::real, calculationYears, 'rivita', calculationScenario)) +
                            (SELECT CO2_BuildDemolish(p.askert::real, calculationYears, 'askert', calculationScenario)) +
                            (SELECT CO2_BuildDemolish(p.liike::real, calculationYears, 'liike', calculationScenario)) +
                            (SELECT CO2_BuildDemolish(p.tsto::real, calculationYears, 'tsto', calculationScenario)) +
                            (SELECT CO2_BuildDemolish(p.liiken::real, calculationYears, 'liiken', calculationScenario)) +
                            (SELECT CO2_BuildDemolish(p.hoito::real, calculationYears, 'hoito', calculationScenario)) +
                            (SELECT CO2_BuildDemolish(p.kokoon::real, calculationYears, 'kokoon', calculationScenario)) +
                            (SELECT CO2_BuildDemolish(p.opetus::real, calculationYears, 'opetus', calculationScenario)) +
                            (SELECT CO2_BuildDemolish(p.teoll::real, calculationYears, 'teoll', calculationScenario)) +
                            (SELECT CO2_BuildDemolish(p.varast::real, calculationYears, 'varast', calculationScenario)) +
                            (SELECT CO2_BuildDemolish(p.muut::real, calculationYears, 'muut', calculationScenario))
                        ) AS rak_purku_co2
                            FROM poistuma_alat p
                                GROUP BY p.xyind
                        ) poistot
                            WHERE results.xyind = poistot.xyind;

            END IF;

            UPDATE results SET
                liikenne_as_tco2 = COALESCE(pop.liikenne_as_co2 * grams_to_tons, 0),
                liikenne_tp_tco2 = COALESCE(pop.liikenne_tp_co2 * grams_to_tons, 0),
                sahko_kotitaloudet_tco2 = COALESCE(results.sahko_kotitaloudet_tco2 + NULLIF(pop.sahko_kotitaloudet_co2_as * grams_to_tons, 0), 0)
            FROM
                (SELECT g.xyind,
                    SUM((SELECT CO2_TrafficPersonal(g.mun, g.pop, calculationYears, 'bussi', centdist, g.zone, calculationScenario, 'pop', includeLongDistance, includeBusinessTravel)) +
                        (SELECT CO2_TrafficPersonal(g.mun, g.pop, calculationYears, 'raide', centdist, g.zone, calculationScenario, 'pop', includeLongDistance, includeBusinessTravel)) +
                        (SELECT CO2_TrafficPersonal(g.mun, g.pop, calculationYears, 'hlauto', centdist, g.zone, calculationScenario, 'pop', includeLongDistance, includeBusinessTravel)) +
                        (SELECT CO2_TrafficPersonal(g.mun, g.pop, calculationYears, 'muu', centdist, g.zone, calculationScenario, 'pop', includeLongDistance, includeBusinessTravel)))
                    AS liikenne_as_co2,
                    SUM((SELECT CO2_TrafficPersonal(g.mun, g.employ, calculationYears, 'bussi', centdist, g.zone, calculationScenario, 'employ', includeLongDistance, includeBusinessTravel)) +
                        (SELECT CO2_TrafficPersonal(g.mun, g.employ, calculationYears, 'raide', centdist, g.zone, calculationScenario, 'employ', includeLongDistance, includeBusinessTravel)) +
                        (SELECT CO2_TrafficPersonal(g.mun, g.employ, calculationYears, 'hlauto', centdist, g.zone, calculationScenario, 'employ', includeLongDistance, includeBusinessTravel)) +
                        (SELECT CO2_TrafficPersonal(g.mun, g.employ, calculationYears, 'muu', centdist, g.zone, calculationScenario, 'employ', includeLongDistance, includeBusinessTravel)))
                    AS liikenne_tp_co2,
                    SUM((SELECT CO2_ElectricityHousehold(g.mun, calculationYears, calculationScenario, g.pop, NULL)))
                    AS sahko_kotitaloudet_co2_as
                    FROM grid g
                        WHERE (g.pop IS NOT NULL AND g.pop > 0)
                        OR (g.employ IS NOT NULL AND g.employ > 0)
                GROUP BY g.xyind) pop
            WHERE pop.xyind = results.xyind;

            IF initialScenario = 'static' AND targetYear IS NOT NULL
                THEN calculationYear := initialYear; calculationYears[1] := initialYear;
            END IF;

            UPDATE results r SET
                year = to_date(calculationYear::varchar, 'YYYY'),
                sum_lammonsaato_tco2 =
                    COALESCE(r.tilat_vesi_tco2, 0) +
                    COALESCE(r.tilat_lammitys_tco2, 0) +
                    COALESCE(r.tilat_jaahdytys_tco2, 0),
                sum_liikenne_tco2 =
                    COALESCE(r.liikenne_as_tco2, 0) +
                    COALESCE(r.liikenne_tp_tco2, 0) +
                    COALESCE(r.liikenne_tv_tco2, 0) +
                    COALESCE(r.liikenne_palv_tco2, 0), 
                sum_sahko_tco2 =
                    COALESCE(r.sahko_kiinteistot_tco2, 0) +
                    COALESCE(r.sahko_kotitaloudet_tco2, 0) +
                    COALESCE(r.sahko_palv_tco2, 0) +
                    COALESCE(r.sahko_tv_tco2, 0),
                sum_rakentaminen_tco2 =
                    COALESCE(r.rak_korjaussaneeraus_tco2, 0) +
                    COALESCE(r.rak_purku_tco2, 0) +
                    COALESCE(r.rak_uudis_tco2, 0);

            UPDATE results r SET
                sum_yhteensa_tco2 =
                    COALESCE(r.sum_lammonsaato_tco2,0) +
                    COALESCE(r.sum_liikenne_tco2,0) +
                    COALESCE(r.sum_sahko_tco2,0) +
                    COALESCE(r.sum_rakentaminen_tco2,0);

            UPDATE results res
            SET floorspace = r.rakyht_ala
            FROM (
                SELECT DISTINCT ON (grid2.xyind) grid2.xyind,
                    SUM(grid2.rakyht_ala) rakyht_ala
                FROM grid2
                    WHERE grid2.rakv::int != 0
                    GROUP BY grid2.xyind
            ) r
            WHERE res.xyind = r.xyind;

            /* Poistetaan purkulaskennoissa käytetty väliaikainen taulu */
            /* Remove the temporary table used in demolishing calculationg */
            DROP TABLE IF EXISTS poistuma_alat;

            IF targetYear IS NULL OR targetYear = calculationYear THEN
                DROP TABLE grid, grid2;
            END IF;

            RETURN QUERY SELECT * FROM results;
            DROP TABLE results;

        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE SCHEMA IF NOT EXISTS functions;

        DROP FUNCTION IF EXISTS functions.CO2_CalculateEmissionsLoop;
        CREATE OR REPLACE FUNCTION
        functions.CO2_CalculateEmissionsLoop(
            municipalities integer[],
            aoi regclass, -- Tutkimusalue | area of interest
            includeLongDistance boolean,
            includeBusinessTravel boolean,
            calculationScenario varchar, -- PITKO:n mukainen scenario
            method varchar, -- Päästöallokointimenetelmä, 'em' tai 'hjm'
            electricityType varchar, -- Sähkön päästölaji, 'hankinta' tai 'tuotanto'
            baseYear integer, -- Laskennan lähtövuosi
            targetYear integer, -- Laskennan tavoitevuosi
            plan_areas regclass default null, -- Taulu, jossa käyttötarkoitusalueet tai vastaavat
            plan_centers regclass default null, -- Taulu, jossa keskusverkkotiedot 
            plan_transit regclass default null -- Taulu, jossa intensiivinen joukkoliikennejärjestelmä,
        )
        RETURNS TABLE(
            geom geometry(MultiPolygon, 3067),
            xyind varchar(13),
            mun int,
            zone bigint,
            year date,
            floorspace int,
            pop smallint,
            employ smallint,
            tilat_vesi_tco2 real,
            tilat_lammitys_tco2 real,
            tilat_jaahdytys_tco2 real,
            sahko_kiinteistot_tco2 real,
            sahko_kotitaloudet_tco2 real,
            sahko_palv_tco2 real,
            sahko_tv_tco2 real,
            liikenne_as_tco2 real,
            liikenne_tp_tco2 real,
            liikenne_tv_tco2 real,
            liikenne_palv_tco2 real,
            rak_korjaussaneeraus_tco2 real,
            rak_purku_tco2 real,
            rak_uudis_tco2 real,
            sum_yhteensa_tco2 real,
            sum_lammonsaato_tco2 real,
            sum_liikenne_tco2 real,
            sum_sahko_tco2 real,
            sum_rakentaminen_tco2 real
        )
        AS $$
        DECLARE
            calculationYears integer[];
            calculationYear integer;
        BEGIN

            SELECT array(select generate_series(baseYear,targetYear))
            INTO calculationYears;

            FOREACH calculationYear in ARRAY calculationYears
            LOOP

                IF calculationYear = baseYear THEN
                    CREATE TEMP TABLE res AS
                    SELECT * FROM
                        CO2_CalculateEmissions(
                            municipalities, aoi, includeLongDistance, includeBusinessTravel, array[calculationYear, 2017, 2050], calculationScenario, method, electricityType, baseYear, targetYear, plan_areas, plan_centers, plan_transit
                        );
                ELSE 
                    INSERT INTO res
                    SELECT * FROM
                        CO2_CalculateEmissions(
                            municipalities, aoi, includeLongDistance, includeBusinessTravel, array[calculationYear, 2017, 2050], calculationScenario, method, electricityType, baseYear, targetYear, plan_areas, plan_centers, plan_transit
                        );
                END IF;
                
            END LOOP;

            UPDATE res SET zone = CASE
                WHEN LEFT(res.zone::varchar, 5)::int IN (99911, 99912) THEN 1
                WHEN LEFT(res.zone::varchar, 5)::int IN (99921, 99922) THEN 2
                WHEN LEFT(res.zone::varchar, 5)::int IN (99931, 99932) THEN 3
                WHEN LEFT(res.zone::varchar, 5)::int IN (99941, 99942) THEN 3
                WHEN LEFT(res.zone::varchar, 5)::int IN (99951, 99952) THEN 3
                WHEN LEFT(res.zone::varchar, 5)::int IN (6, 99961, 99962, 99901, 99902, 99910) THEN 10
                WHEN LEFT(res.zone::varchar, 5)::int IN (99981, 99982, 99983, 99984, 99985, 99986, 99987) THEN RIGHT(LEFT(res.zone::varchar, 5),2)::int
            ELSE res.zone END;

            RETURN QUERY SELECT * FROM res;
            DROP TABLE IF EXISTS res;

        END;
        $$ LANGUAGE plpgsql;
    """)

def downgrade() -> None:
    pass
