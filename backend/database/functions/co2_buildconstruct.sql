/* Uudisrakentaminen (energia) | Construction of new buildings (energy)
YKR-ruudun laskentavuoden uudisrakentamisen energian kasvihuonekaasupäästöt [CO2-ekv/a] lasketaan seuraavasti:
    rak_uusi_energia_co2 = rakennus_ala * rak_energia_gco2m2
YKR-ruudun laskentavuoden uudisrakentamisen rakennustuotteiden kasvihuonekaasupäästöt rak_uusi_materia_co2 [CO2-ekv/a] lasketaan seuraavasti:
    rak_uusi_materia_co2 = rakennus_ala * rak_materia_gco2m2 */
CREATE SCHEMA IF NOT EXISTS functions;
DROP FUNCTION IF EXISTS functions.CO2_BuildConstruct;
CREATE OR REPLACE FUNCTION
functions.CO2_BuildConstruct(
	floorSpace real, -- Rakennustyypin tietyn ikäluokan kerrosala YKR-ruudussa laskentavuonna [m2]. Lukuarvo riippuu laskentavuodesta ja rakennuksen tyypistä.
    calculationYear integer, -- [year based on which emission values are calculated, min, max calculation years]
    buildingType varchar, -- Rakennustyyppi, esim. 'erpien', 'rivita'
    calculationScenario varchar -- PITKO:n mukainen kehitysskenaario
)
RETURNS real AS
$$
DECLARE
    construction_energy_gco2m2 real; -- Rakennustyypin rakentamisvaiheen työmaatoimintojen ja kuljetusten kasvihuonekaasujen ominaispäästöjä yhtä rakennettua kerrosneliötä kohti [gCO2-ekv/m2]. Arvo riippuu taustaskenaariosta, tarkasteluvuodesta ja rakennustyypistä.
    construction_materials_gco2m2 real; -- Rakennustyypin rakentamiseen tarvittujen rakennustuotteiden tuotantoprosessin välillisiä kasvihuonekaasujen ominaispäästöjä yhtä rakennettua kerrosneliötä kohti [gCO2-ekv/m2]. Arvo riippuu taustaskenaariosta, tarkasteluvuodesta ja rakennustyypistä.
BEGIN

/* Returning zero, if grid cell has 0, -1 or NULL built floor area */
IF floorSpace <= 0 OR floorSpace IS NULL THEN
    RETURN 0;
ELSE

    /* Haetaan laskentavuoden ja kehitysskenaarion perusteella rakennustyyppikohtaiset uudisrakentamisen energiankulutuksen kasvihuonekaasupäästöt */
    EXECUTE 'SELECT ' || buildingType || ' FROM built.build_new_construction_energy_gco2m2
        WHERE year = $1 AND scenario = $2 LIMIT 1'
        INTO construction_energy_gco2m2 USING calculationYear, calculationScenario;
    
    /* Haetaan laskentavuoden ja kehitysskenaarion perusteella rakennustyyppikohtaiset uudisrakentamisen materiaalien valmistuksen kasvihuonekaasupäästöt */
    EXECUTE 'SELECT ' || CASE WHEN buildingType IN ('erpien', 'rivita', 'askert')
        THEN buildingType
            ELSE 'muut'
        END || ' 
            FROM built.build_materia_gco2m2
            WHERE year = $1 AND scenario = $2 LIMIT 1'
        INTO construction_materials_gco2m2
            USING calculationYear, calculationScenario;

    /* Lasketaan ja palautetaan päästöt CO2-ekvivalenttia [gCO2-ekv/v] */
    RETURN floorSpace * 
        (COALESCE(construction_energy_gco2m2,0) + COALESCE(construction_materials_gco2m2, 0));

END IF;

END;
$$ LANGUAGE plpgsql;