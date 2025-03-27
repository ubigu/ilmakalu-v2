CREATE SCHEMA IF NOT EXISTS functions;
DROP FUNCTION IF EXISTS functions.CO2_UpdateBuildingsLocal;
CREATE OR REPLACE FUNCTION
functions.CO2_UpdateBuildingsLocal(
    rak_taulu text,
    ykr_taulu text,
    calculationYear int, -- [year based on which emission values are calculated, min, max calculation years]
    baseYear int,
	targetYear int,
    kehitysskenaario varchar -- PEIKKO:n mukainen kehitysskenaario
)
RETURNS TABLE (
    xyind varchar,
    rakv int,
	energiam varchar,
    rakyht_ala int, 
    asuin_ala int,
    erpien_ala int,
    rivita_ala int,
    askert_ala int,
    liike_ala int,
    myymal_ala int,
    majoit_ala int,
    asla_ala int,
    ravint_ala int,
    tsto_ala int,
    liiken_ala int,
    hoito_ala int,
    kokoon_ala int,
    opetus_ala int,
    teoll_ala int,
    varast_ala int,
    muut_ala int
) AS $$
DECLARE
	energiamuoto varchar;
	energyarray real[];
	laskentavuodet int[];
	laskenta_length int;
	step real;
	localweight real;
	globalweight real;
    teoll_koko real;
    varast_koko real;
BEGIN

-- energiamuodot := ARRAY [kaukolampo, kevyt_oljy, raskas_oljy, kaasu, sahko, puu, turve, hiili, maalampo, muu_lammitys];
SELECT array(select generate_series(baseYear,targetYear)) INTO laskentavuodet;
SELECT array_length(laskentavuodet,1) into laskenta_length;
SELECT 1::real / laskenta_length INTO step;
SELECT (calculationYear - baseYear + 1) * step INTO globalweight;
SELECT 1 - globalweight INTO localweight;

EXECUTE 'CREATE TEMP TABLE IF NOT EXISTS ykr AS SELECT xyind, zone, alueteho, maa_ha, k_ap_ala, k_ar_ala, k_ak_ala, k_muu_ala, k_poistuma FROM ' || quote_ident(ykr_taulu) || ' WHERE (k_ap_ala IS NOT NULL AND k_ap_ala != 0) OR (k_ar_ala IS NOT NULL AND k_ar_ala != 0) OR (k_ak_ala IS NOT NULL AND k_ak_ala != 0) OR (k_muu_ala IS NOT NULL AND k_muu_ala != 0) OR (k_poistuma IS NOT NULL AND k_poistuma != 0)';
EXECUTE 'CREATE TEMP TABLE IF NOT EXISTS rak AS SELECT xyind, rakv::int, energiam::varchar, rakyht_ala::int, asuin_ala::int, erpien_ala::int, rivita_ala::int, askert_ala::int, liike_ala::int, myymal_ala::int, majoit_ala::int, asla_ala::int, ravint_ala::int, tsto_ala::int, liiken_ala::int, hoito_ala::int, kokoon_ala::int, opetus_ala::int, teoll_ala::int, varast_ala::int, muut_ala::int FROM ' || quote_ident(rak_taulu) ||' WHERE rakv::int != 0';

ANALYZE rak;
CREATE INDEX rak_index ON rak (xyind, rakv, energiam);

/* Haetaan globaalit lämmitysmuotojakaumat laskentavuodelle ja -skenaariolle */
/* Fetching global heating ratios for current calculation year and scenario */
CREATE TEMP TABLE IF NOT EXISTS global_jakauma AS
	SELECT rakennus_tyyppi, kaukolampo / (kaukolampo + sahko + puu + maalampo + muu_lammitys) AS kaukolampo,
	sahko / (kaukolampo + sahko+puu+maalampo + muu_lammitys) AS sahko,
	puu / (kaukolampo+sahko+puu+maalampo+muu_lammitys) AS puu,
	maalampo / (kaukolampo+sahko+puu+maalampo+muu_lammitys) AS maalampo,
	muu_lammitys / (kaukolampo+sahko+puu+maalampo+muu_lammitys) AS muu_lammitys
	FROM built.distribution_heating_systems dhs
	WHERE dhs.year = calculationYear AND dhs.rakv = calculationYear AND dhs.scenario = kehitysskenaario;

/* Add aggregate sums for general heating system distributions */
INSERT INTO global_jakauma (rakennus_tyyppi, kaukolampo, sahko, puu, maalampo)
	SELECT 'rakyht', avg(kaukolampo), avg(sahko), avg(puu), avg(maalampo)
	FROM global_jakauma;

/* Puretaan rakennuksia 0.0015 */
/* Demolishing buildings */
UPDATE rak b SET
    erpien_ala = GREATEST(b.erpien_ala - erpien, 0),
    rivita_ala = GREATEST(b.rivita_ala - rivita, 0),
    askert_ala = GREATEST(b.askert_ala - askert, 0),
    liike_ala = GREATEST(b.liike_ala - liike, 0),
    myymal_ala = GREATEST(b.myymal_ala - myymal, 0),
    majoit_ala = GREATEST(b.majoit_ala - majoit, 0),
    asla_ala = GREATEST(b.asla_ala - asla, 0),
    ravint_ala = GREATEST(b.ravint_ala - ravint, 0),
    tsto_ala = GREATEST(b.tsto_ala - tsto, 0),
    liiken_ala = GREATEST(b.liiken_ala - liiken, 0),
    hoito_ala = GREATEST(b.hoito_ala - hoito, 0),
    kokoon_ala = GREATEST(b.kokoon_ala - kokoon, 0),
    opetus_ala = GREATEST(b.opetus_ala - opetus, 0),
    teoll_ala = GREATEST(b.teoll_ala - teoll, 0),
    varast_ala = GREATEST(b.varast_ala - varast, 0),
    muut_ala = GREATEST(b.muut_ala - muut, 0)
FROM (
WITH poistuma AS (
    SELECT ykr.xyind, GREATEST(SUM(k_poistuma), SUM(alueteho * maa_ha * 10000) * 0.0015) poistuma FROM ykr GROUP BY ykr.xyind
),
buildings AS (
	SELECT rak.xyind, rak.rakv,
		rak.erpien_ala :: real / NULLIF(grouped.rakyht_ala, 0) erpien,
		rak.rivita_ala :: real / NULLIF(grouped.rakyht_ala, 0) rivita,
		rak.askert_ala :: real / NULLIF(grouped.rakyht_ala, 0) askert,
		rak.liike_ala :: real / NULLIF(grouped.rakyht_ala, 0) liike,
        rak.myymal_ala :: real / NULLIF(grouped.rakyht_ala, 0) myymal,
        rak.majoit_ala :: real / NULLIF(grouped.rakyht_ala, 0) majoit,
        rak.asla_ala :: real / NULLIF(grouped.rakyht_ala, 0) asla,
        rak.ravint_ala :: real / NULLIF(grouped.rakyht_ala, 0) ravint,
		rak.tsto_ala :: real / NULLIF(grouped.rakyht_ala, 0) tsto,
		rak.liiken_ala :: real / NULLIF(grouped.rakyht_ala, 0) liiken,
		rak.hoito_ala :: real / NULLIF(grouped.rakyht_ala, 0) hoito,
		rak.kokoon_ala :: real / NULLIF(grouped.rakyht_ala, 0) kokoon,
		rak.opetus_ala :: real / NULLIF(grouped.rakyht_ala, 0) opetus,
		rak.teoll_ala :: real / NULLIF(grouped.rakyht_ala, 0) teoll,
		rak.varast_ala:: real / NULLIF(grouped.rakyht_ala, 0) varast,
		rak.muut_ala :: real / NULLIF(grouped.rakyht_ala, 0) muut
	FROM rak JOIN
	(SELECT build2.xyind, SUM(build2.rakyht_ala) rakyht_ala FROM rak build2 GROUP BY build2.xyind) grouped
	ON grouped.xyind = rak.xyind
	WHERE rak.rakv != calculationYear
)
SELECT poistuma.xyind,
	buildings.rakv,
	poistuma * erpien erpien,
	poistuma * rivita rivita,
	poistuma * askert askert,
	poistuma * liike liike,
    poistuma * myymal myymal,
	poistuma * majoit majoit,
	poistuma * asla asla,
	poistuma * ravint ravint,
	poistuma * tsto tsto,
	poistuma * liiken liiken,
	poistuma * hoito hoito,
	poistuma * kokoon kokoon,
	poistuma * opetus opetus,
	poistuma * teoll teoll,
	poistuma * varast varast,
	poistuma * muut muut
FROM poistuma LEFT JOIN buildings ON buildings.xyind = poistuma.xyind
WHERE poistuma > 0 AND buildings.rakv IS NOT NULL) poistumat
WHERE b.xyind = poistumat.xyind AND b.rakv = poistumat.rakv;

UPDATE rak SET energiam = 'muu_lammitys' WHERE rak.energiam IS NULL;

/* Lisätään puuttuvat sarakkeet väliaikaiseen YKR-dataan */
/* Adding new columns into the temporary YKR data */
ALTER TABLE ykr
    ADD COLUMN liike_osuus real,
    ADD COLUMN myymal_osuus real,
    ADD COLUMN majoit_osuus real,
    ADD COLUMN asla_osuus real,
    ADD COLUMN ravint_osuus real,
    ADD COLUMN tsto_osuus real,
    ADD COLUMN liiken_osuus real,
    ADD COLUMN hoito_osuus real,
    ADD COLUMN kokoon_osuus real,
    ADD COLUMN opetus_osuus real,
    ADD COLUMN teoll_osuus real,
    ADD COLUMN varast_osuus real,
    ADD COLUMN muut_osuus real,
    ADD COLUMN muu_ala real;

ANALYZE ykr;
CREATE INDEX ykr_xyind_index ON ykr (xyind);

/* Lasketaan myös vakiokäyttötapausjakaumat uusia alueita varten */
/* Käyttöalaperusteinen käyttötapajakauma generoidaan rakennusdatasta UZ-vyöhykkeittäin */
/* Calculate default proportions of building usage for new areas as well */
CREATE TEMP TABLE IF NOT EXISTS kayttotapajakauma AS 
SELECT ykr.zone,
	COALESCE(SUM(r.liike_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as liike_osuus,
	COALESCE(SUM(r.myymal_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as myymal_osuus,
	COALESCE(SUM(r.majoit_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as majoit_osuus,
	COALESCE(SUM(r.asla_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as asla_osuus,
	COALESCE(SUM(r.ravint_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as ravint_osuus,
	COALESCE(SUM(r.tsto_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as tsto_osuus,
	COALESCE(SUM(r.liiken_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as liiken_osuus,
	COALESCE(SUM(r.hoito_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as hoito_osuus,
	COALESCE(SUM(r.kokoon_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as kokoon_osuus,
	COALESCE(SUM(r.opetus_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as opetus_osuus,
	COALESCE(SUM(r.teoll_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as teoll_osuus,
	COALESCE(SUM(r.varast_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as varast_osuus,
	COALESCE(SUM(r.muut_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as muut_osuus
FROM rak r JOIN ykr ON r.xyind = ykr.xyind
GROUP BY ykr.zone;

UPDATE kayttotapajakauma j SET 
	liike_osuus = ktj.liike_osuus,
	myymal_osuus = ktj.myymal_osuus,
	majoit_osuus = ktj.majoit_osuus,
	asla_osuus = ktj.asla_osuus,
	ravint_osuus = ktj.ravint_osuus,
	tsto_osuus = ktj.tsto_osuus,
	liiken_osuus = ktj.liiken_osuus,
	hoito_osuus = ktj.hoito_osuus,
	kokoon_osuus = ktj.kokoon_osuus,
	opetus_osuus = ktj.opetus_osuus,
	teoll_osuus = ktj.teoll_osuus,
	varast_osuus = ktj.varast_osuus,
	muut_osuus = ktj.muut_osuus
FROM
(SELECT
	AVG(k.liike_osuus) liike_osuus,
	AVG(k.myymal_osuus) myymal_osuus,
	AVG(k.majoit_osuus) majoit_osuus,
	AVG(k.asla_osuus) asla_osuus,
	AVG(k.ravint_osuus) ravint_osuus,
	AVG(k.tsto_osuus) tsto_osuus,
	AVG(k.liiken_osuus) liiken_osuus,
	AVG(k.hoito_osuus) hoito_osuus,
	AVG(k.kokoon_osuus) kokoon_osuus,
	AVG(k.opetus_osuus) opetus_osuus,
	AVG(k.teoll_osuus) teoll_osuus,
	AVG(k.varast_osuus) varast_osuus,
	AVG(k.muut_osuus) muut_osuus
FROM kayttotapajakauma k
	WHERE k.liike_osuus + k.tsto_osuus + k.liiken_osuus + k.hoito_osuus + k.kokoon_osuus + k.opetus_osuus + k.teoll_osuus + k.varast_osuus + k.muut_osuus > 0.99
) ktj
WHERE j.liike_osuus + j.tsto_osuus + j.liiken_osuus + j.hoito_osuus + j.kokoon_osuus + j.opetus_osuus + j.teoll_osuus + j.varast_osuus + j.muut_osuus <= 0.99;

UPDATE ykr SET
    liike_osuus = ktj.liike_osuus,
    myymal_osuus = ktj.myymal_osuus,
    majoit_osuus = ktj.majoit_osuus,
    asla_osuus = ktj.asla_osuus,
    ravint_osuus = ktj.ravint_osuus,
    tsto_osuus = ktj.tsto_osuus,
    liiken_osuus = ktj.liiken_osuus,
    hoito_osuus = ktj.hoito_osuus,
    kokoon_osuus = ktj.kokoon_osuus,
    opetus_osuus = ktj.opetus_osuus,
    teoll_osuus = ktj.teoll_osuus,
    varast_osuus = ktj.varast_osuus,
    muut_osuus = ktj.muut_osuus
FROM kayttotapajakauma ktj
WHERE ykr.zone = ktj.zone;

/* Lasketaan nykyisen paikallisesta rakennusdatasta muodostetun ruutuaineiston mukainen ruutukohtainen energiajakauma rakennustyypeittäin */
/* Laskenta tehdään vain 2000-luvulta eteenpäin rakennetuille tai rakennettaville rakennuksille */
CREATE TEMP TABLE IF NOT EXISTS local_jakauma AS
SELECT rakennus_tyyppi, 
	SUM(ala) FILTER (WHERE sq.energiam = 'kaukolampo') / SUM(ala) AS kaukolampo,
	SUM(ala) FILTER (WHERE sq.energiam = 'sahko') / SUM(ala) AS sahko,
	SUM(ala) FILTER (WHERE sq.energiam = 'puu') / SUM(ala) AS puu,
	SUM(ala) FILTER (WHERE sq.energiam = 'maalampo') / SUM(ala) AS maalampo,
	SUM(ala) FILTER (WHERE sq.energiam = 'muu_lammitys') / SUM(ala) AS muu_lammitys
FROM
(SELECT 
	UNNEST(ARRAY['rakyht','erpien','rivita','askert','liike','tsto','liiken','hoito','kokoon','opetus','teoll','varast','muut']) AS rakennus_tyyppi,
    rak.energiam,
	UNNEST(ARRAY[
		SUM(rak.rakyht_ala), 
		SUM(rak.erpien_ala), 
		SUM(rak.rivita_ala), 
		SUM(rak.askert_ala), 
		SUM(rak.liike_ala), 
		SUM(rak.tsto_ala),
		SUM(rak.liiken_ala), 
		SUM(rak.hoito_ala), 
		SUM(rak.kokoon_ala),
		SUM(rak.opetus_ala),
		SUM(rak.teoll_ala),
		SUM(rak.varast_ala),
		SUM(rak.muut_ala)]
	) as ala
FROM rak
	WHERE rak.rakv > 2000 AND rak.energiam NOT IN ('kaasu', 'kevyt_oljy')
	GROUP BY rak.energiam) sq
GROUP BY rakennus_tyyppi;

/* Päivitetään paikallisen lämmitysmuotojakauman ja kansallisen lämmitysmuotojakauman erot */
/* Updating differences between local and "global" heating distributions */
UPDATE local_jakauma AS l SET
kaukolampo = CASE 
    	WHEN l.kaukolampo IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN g.kaukolampo
    	ELSE localweight * COALESCE(l.kaukolampo, 0) + globalweight * g.kaukolampo END,
    sahko = CASE 
        WHEN l.kaukolampo IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN g.sahko
        ELSE localweight * COALESCE(l.sahko, 0) + globalweight * g.sahko END,
    puu = CASE 
        WHEN l.kaukolampo IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN g.puu
        ELSE localweight * COALESCE(l.puu, 0) + globalweight * g.puu END,
    maalampo = CASE 
        WHEN l.kaukolampo IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN g.maalampo
        ELSE localweight * COALESCE(l.maalampo, 0) + globalweight * g.maalampo END,
    muu_lammitys = CASE 
        WHEN l.kaukolampo IS NULL AND l.sahko IS NULL AND l.puu IS NULL AND l.maalampo IS NULL AND l.muu_lammitys IS NULL THEN g.muu_lammitys
        ELSE localweight * COALESCE(l.muu_lammitys, 0) + globalweight * g.muu_lammitys END
FROM global_jakauma g
WHERE l.rakennus_tyyppi =  g.rakennus_tyyppi;

/* Rakennetaan uudet rakennukset energiamuodoittain */
/* Building new buildings, per primary energy source */

FOREACH energiamuoto IN ARRAY ARRAY['kaukolampo', 'sahko', 'puu', 'maalampo', 'muu_lammitys']
LOOP

/* This creates an array of [1: askert, 2: erpien, 3: hoito, 4: kokoon, 5: liike, 6: liiken, 7: muut, 8: opetus, 9: rakyht, 10: rivita, 11: teoll, 12: tsto, 13: varast] */
EXECUTE FORMAT('SELECT ARRAY(
	SELECT %1$I::real
	FROM local_jakauma
	ORDER BY rakennus_tyyppi ASC)', energiamuoto) 
INTO energyarray;

    INSERT INTO rak (xyind, rakv, energiam, rakyht_ala, asuin_ala, erpien_ala, rivita_ala, askert_ala, liike_ala, myymal_ala, majoit_ala, asla_ala, ravint_ala, tsto_ala, liiken_ala, hoito_ala, kokoon_ala, opetus_ala, teoll_ala, varast_ala, muut_ala)
	SELECT
		ykr.xyind, -- xyind
        calculationYear, -- rakv
		energiamuoto, -- energiam
        NULL::int, -- rakyht_ala
        NULL::int, --asuin_ala
        k_ap_ala * (energyarray)[2], -- erpien_ala
        k_ar_ala * (energyarray)[10], -- rivita_ala
        k_ak_ala * (energyarray)[1], -- askert_ala
        liike_osuus * k_muu_ala * (energyarray)[5], -- liike_ala
        myymal_osuus * k_muu_ala * (energyarray)[5], --myymal_ala
        majoit_osuus * k_muu_ala * (energyarray)[5], -- majoit_ala
        asla_osuus * k_muu_ala * (energyarray)[5], -- asla_ala
        ravint_osuus * k_muu_ala * (energyarray)[5], -- ravint_ala
        tsto_osuus * k_muu_ala * (energyarray)[12], -- tsto_ala
        liiken_osuus * k_muu_ala * (energyarray)[6], -- liiken_ala
        hoito_osuus * k_muu_ala * (energyarray)[3], -- hoito_ala
        kokoon_osuus * k_muu_ala * (energyarray)[4], -- kokoon_ala
        opetus_osuus * k_muu_ala * (energyarray)[8], -- opetus_ala
        teoll_osuus * k_muu_ala * (energyarray)[11], -- teoll_ala
        varast_osuus * k_muu_ala * (energyarray)[13], -- varast_ala
        muut_osuus * k_muu_ala * (energyarray)[7] -- muut_ala
    FROM ykr;

energyarray := NULL;

END LOOP;

UPDATE rak SET
	asuin_ala = COALESCE(rak.erpien_ala,0) + COALESCE(rak.rivita_ala,0) + COALESCE(rak.askert_ala,0)
WHERE rak.rakv = calculationYear AND rak.asuin_ala IS NULL;

UPDATE rak SET
	rakyht_ala = COALESCE(rak.asuin_ala,0) + COALESCE(rak.liike_ala,0) + COALESCE(rak.tsto_ala,0) + COALESCE(rak.liiken_ala,0) +
	COALESCE(rak.hoito_ala,0) + COALESCE(rak.kokoon_ala,0) + COALESCE(rak.opetus_ala, 0) + COALESCE(rak.teoll_ala, 0) +
	COALESCE(rak.varast_ala, 0) + COALESCE(rak.muut_ala, 0) 
WHERE rak.rakv = calculationYear AND rak.rakyht_ala IS NULL;

DELETE FROM rak WHERE rak.rakyht_ala = 0;

/* Päivitetään vanhojen pytinkien lämmitysmuodot */
/* Updating heating characteristics of old buildings */

CREATE TEMP TABLE IF NOT EXISTS rak_temp AS
SELECT DISTINCT ON (r.xyind, r.rakv, energiam) r.xyind, r.rakv,
UNNEST(CASE
WHEN muu_lammitys IS NULL AND kevyt_oljy IS NULL AND kaasu IS NULL THEN
	ARRAY['kaukolampo', 'sahko', 'puu', 'maalampo'] 
WHEN muu_lammitys IS NULL THEN
	ARRAY['kaukolampo', 'kevyt_oljy', 'kaasu', 'sahko', 'puu', 'maalampo'] 
ELSE ARRAY['kaukolampo', 'kevyt_oljy', 'kaasu', 'sahko', 'puu', 'maalampo', 'muu_lammitys'] END)::varchar AS energiam,
NULL::int AS rakyht_ala, NULL::int AS asuin_ala, NULL::int AS erpien_ala, NULL::int AS rivita_ala, NULL::int AS askert_ala,
NULL::int AS liike_ala, NULL::int AS myymal_ala, NULL::int AS majoit_ala, NULL::int AS asla_ala, NULL::int AS ravint_ala, 
NULL::int AS tsto_ala, NULL::int AS liiken_ala, NULL::int AS hoito_ala, NULL::int AS kokoon_ala, NULL::int AS opetus_ala,
NULL::int AS teoll_ala, NULL::int AS varast_ala, NULL::int AS muut_ala
from rak r
LEFT JOIN 
(WITH
	kaukolampo AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam = 'kaukolampo'),
	kevyt_oljy AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili')),
	kaasu AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam = 'kaasu'),
	sahko AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam = 'sahko'),
	puu AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam = 'puu'),
	maalampo AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam = 'maalampo'),
	muu_lammitys AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam = 'muu_lammitys')
SELECT distinct on (r2.xyind, r2.rakv) r2.xyind, r2.rakv,
	kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys
FROM rak r2
	LEFT JOIN kaukolampo on r2.xyind = kaukolampo.xyind AND r2.rakv = kaukolampo.rakv 
	LEFT JOIN kevyt_oljy on r2.xyind = kevyt_oljy.xyind AND r2.rakv = kevyt_oljy.rakv 
	LEFT JOIN kaasu on r2.xyind = kaasu.xyind AND r2.rakv = kaasu.rakv 
	LEFT JOIN sahko on r2.xyind = sahko.xyind AND r2.rakv = sahko.rakv 
	LEFT JOIN puu on r2.xyind = puu.xyind AND r2.rakv = puu.rakv
	LEFT JOIN maalampo on r2.xyind = maalampo.xyind AND r2.rakv = maalampo.rakv 
	LEFT JOIN muu_lammitys on r2.xyind = muu_lammitys.xyind AND r2.rakv = muu_lammitys.rakv
WHERE r2.rakv < 2019
	) sq 
ON sq.xyind = r.xyind AND sq.rakv = r.rakv where r.rakv < 2019;

ANALYZE rak_temp;
CREATE INDEX rak_temp_rakv_index ON rak_temp (rakv);
CREATE INDEX rak_temp_energiam_index ON rak_temp (energiam);

UPDATE rak_temp future set rakyht_ala = past.rakyht_ala,
	asuin_ala = past.asuin_ala, erpien_ala = past.erpien_ala, rivita_ala = past.rivita_ala, askert_ala = past.askert_ala, liike_ala = past.liike_ala, myymal_ala = past.myymal_ala,
	majoit_ala = past.majoit_ala, asla_ala = past.asla_ala, ravint_ala = past.ravint_ala,  tsto_ala = past.tsto_ala, liiken_ala = past.liiken_ala, hoito_ala = past.hoito_ala, kokoon_ala = past.kokoon_ala,
	opetus_ala = past.opetus_ala, teoll_ala = past.teoll_ala, varast_ala = past.varast_ala, muut_ala = past.muut_ala
FROM rak past WHERE future.xyind = past.xyind AND future.rakv = past.rakv AND future.energiam = past.energiam;

CREATE TEMP TABLE IF NOT EXISTS rak_new AS 
SELECT * FROM (
	WITH muutos AS (
 		SELECT sq.xyind, sq.rakv,
			ARRAY[sum(erpien[1]), sum(erpien[2]), sum(erpien[3]), sum(erpien[4]), sum(erpien[5]), sum(erpien[6])] as erpien,
			ARRAY[sum(rivita[1]), sum(rivita[2]), sum(rivita[3]), sum(rivita[4]), sum(rivita[5]), sum(rivita[6])] as rivita,
			ARRAY[sum(askert[1]), sum(askert[2]), sum(askert[3]), sum(askert[4]), sum(askert[5]), sum(askert[6])] as askert,
			ARRAY[sum(liike[1]), sum(liike[2]), sum(liike[3]), sum(liike[4]), sum(liike[5]), sum(liike[6])] as liike,
			ARRAY[sum(myymal[1]), sum(myymal[2]), sum(myymal[3]), sum(myymal[4]), sum(myymal[5]), sum(myymal[6])] as myymal,
			ARRAY[sum(majoit[1]), sum(majoit[2]), sum(majoit[3]), sum(majoit[4]), sum(majoit[5]), sum(majoit[6])] as majoit,
			ARRAY[sum(asla[1]), sum(asla[2]), sum(asla[3]), sum(asla[4]), sum(asla[5]), sum(asla[6])] as asla,
			ARRAY[sum(ravint[1]), sum(ravint[2]), sum(ravint[3]), sum(ravint[4]), sum(ravint[5]), sum(ravint[6])] as ravint,
			ARRAY[sum(tsto[1]), sum(tsto[2]), sum(tsto[3]), sum(tsto[4]), sum(tsto[5]), sum(tsto[6])] as tsto,
			ARRAY[sum(liiken[1]), sum(liiken[2]), sum(liiken[3]), sum(liiken[4]), sum(liiken[5]), sum(liiken[6])] as liiken,
			ARRAY[sum(hoito[1]), sum(hoito[2]), sum(hoito[3]), sum(hoito[4]), sum(hoito[5]), sum(hoito[6])] as hoito,
			ARRAY[sum(kokoon[1]), sum(kokoon[2]), sum(kokoon[3]), sum(kokoon[4]), sum(kokoon[5]), sum(kokoon[6])] as kokoon,
			ARRAY[sum(opetus[1]), sum(opetus[2]), sum(opetus[3]), sum(opetus[4]), sum(opetus[5]), sum(opetus[6])] as opetus,
			ARRAY[sum(teoll[1]), sum(teoll[2]), sum(teoll[3]), sum(teoll[4]), sum(teoll[5]), sum(teoll[6])] as teoll,
			ARRAY[sum(varast[1]), sum(varast[2]), sum(varast[3]), sum(varast[4]), sum(varast[5]), sum(varast[6])] as varast,
			ARRAY[sum(muut[1]), sum(muut[2]), sum(muut[3]), sum(muut[4]), sum(muut[5]), sum(muut[6])] as muut
 		FROM (SELECT t.xyind, t.rakv, t.energiam,
 
 		(CASE WHEN t.erpien_ala IS NOT NULL AND NOT(t.erpien_ala <= 0) THEN ARRAY(SELECT t.erpien_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'erpien' AND lammitysmuoto = t.energiam)
        )) END) as erpien,
 		(CASE WHEN t.rivita_ala IS NOT NULL AND NOT(t.rivita_ala <= 0) THEN ARRAY(SELECT t.rivita_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'rivita' AND lammitysmuoto = t.energiam)
        )) END) as rivita,
 		(CASE WHEN t.askert_ala IS NOT NULL AND NOT(t.askert_ala <= 0) THEN ARRAY(SELECT t.askert_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'askert' AND lammitysmuoto = t.energiam)
        )) END) as askert, 
 		(CASE WHEN t.liike_ala IS NOT NULL AND NOT(t.liike_ala <= 0) THEN ARRAY(SELECT t.liike_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
        )) END) as liike,
 		(CASE WHEN t.myymal_ala IS NOT NULL AND NOT(t.myymal_ala <= 0) THEN ARRAY(SELECT t.myymal_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
        )) END) as myymal,
 		(CASE WHEN t.majoit_ala IS NOT NULL AND NOT(t.majoit_ala <= 0) THEN ARRAY(SELECT t.majoit_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
        )) END) as majoit,
 		(CASE WHEN t.asla_ala IS NOT NULL AND NOT(t.asla_ala <= 0) THEN ARRAY(SELECT t.asla_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
        )) END) as asla,
 		(CASE WHEN t.ravint_ala IS NOT NULL AND NOT(t.ravint_ala <= 0) THEN ARRAY(SELECT t.ravint_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liike' AND lammitysmuoto = t.energiam)
        )) END) as ravint,
 		(CASE WHEN t.tsto_ala IS NOT NULL AND NOT(t.tsto_ala <= 0) THEN ARRAY(SELECT t.tsto_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'tsto' AND lammitysmuoto = t.energiam)
        )) END) as tsto, 
 		(CASE WHEN t.liiken_ala IS NOT NULL AND NOT(t.liiken_ala <= 0) THEN ARRAY(SELECT t.liiken_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'liiken' AND lammitysmuoto = t.energiam)
        )) END) as liiken,
 		(CASE WHEN t.hoito_ala IS NOT NULL AND NOT(t.hoito_ala <= 0) THEN ARRAY(SELECT t.hoito_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'hoito' AND lammitysmuoto = t.energiam)
        )) END) as hoito,
 		(CASE WHEN t.kokoon_ala IS NOT NULL AND NOT(t.kokoon_ala <= 0) THEN ARRAY(SELECT t.kokoon_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'kokoon' AND lammitysmuoto = t.energiam)
        )) END) as kokoon,
 		(CASE WHEN t.opetus_ala IS NOT NULL AND NOT(t.opetus_ala <= 0) THEN ARRAY(SELECT t.opetus_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'opetus' AND lammitysmuoto = t.energiam)
        )) END) as opetus,
		(CASE WHEN t.teoll_ala IS NOT NULL AND NOT(t.teoll_ala <= 0) THEN ARRAY(SELECT t.teoll_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'teoll' AND lammitysmuoto = t.energiam)
		)) END) as teoll,
		(CASE WHEN t.varast_ala IS NOT NULL AND NOT(t.varast_ala <= 0) THEN ARRAY(SELECT t.varast_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'varast' AND lammitysmuoto = t.energiam)
		)) END) as varast,
		(CASE WHEN t.muut_ala IS NOT NULL AND NOT(t.muut_ala <= 0) THEN ARRAY(SELECT t.muut_ala * 
			UNNEST((SELECT ARRAY[kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo] FROM energy."heat_source_change" WHERE scenario = kehitysskenaario AND rakennus_tyyppi = 'muut' AND lammitysmuoto = t.energiam)
		)) END) as muut
 	FROM rak_temp t WHERE t.rakv != 0
	) sq
GROUP BY sq.rakv, sq.xyind)

SELECT rak_temp.xyind, rak_temp.rakv, rak_temp.energiam, -- Seuraaviin voisi rakentaa kytkimen, jolla alle nollan menevät NULLAtaan, mutta nyt jätetty pois koska moiset pudotetaan laskennassa pois joka tapauksessa
	NULL::int as rakyht_ala, 
	NULL::int as asuin_ala,
	NULLIF(COALESCE(rak_temp.erpien_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN erpien[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN erpien[2]
		WHEN rak_temp.energiam = 'kaasu' THEN erpien[3]
		WHEN rak_temp.energiam = 'sahko' THEN erpien[4]
		WHEN rak_temp.energiam = 'puu' THEN erpien[5]
		WHEN rak_temp.energiam = 'maalampo' THEN erpien[6]
		ELSE 0 END),0)::int
	as erpien_ala,
	NULLIF(COALESCE(rak_temp.rivita_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN rivita[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN rivita[2]
		WHEN rak_temp.energiam = 'kaasu' THEN rivita[3]
		WHEN rak_temp.energiam = 'sahko' THEN rivita[4]
		WHEN rak_temp.energiam = 'puu' THEN rivita[5]
		WHEN rak_temp.energiam = 'maalampo' THEN rivita[6]
		ELSE 0 END),0)::int
	as rivita_ala,
	NULLIF(COALESCE(rak_temp.askert_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN askert[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN askert[2]
		WHEN rak_temp.energiam = 'kaasu' THEN askert[3]
		WHEN rak_temp.energiam = 'sahko' THEN askert[4]
		WHEN rak_temp.energiam = 'puu' THEN askert[5]
		WHEN rak_temp.energiam = 'maalampo' THEN askert[6]
		ELSE 0 END),0)::int
	as askert_ala,
	NULLIF(COALESCE(rak_temp.liike_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN liike[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN liike[2]
		WHEN rak_temp.energiam = 'kaasu' THEN liike[3]
		WHEN rak_temp.energiam = 'sahko' THEN liike[4]
		WHEN rak_temp.energiam = 'puu' THEN liike[5]
		WHEN rak_temp.energiam = 'maalampo' THEN liike[6]
		ELSE 0 END),0)::int
	as liike_ala,
	NULLIF(COALESCE(rak_temp.myymal_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN myymal[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN myymal[2]
		WHEN rak_temp.energiam = 'kaasu' THEN myymal[3]
		WHEN rak_temp.energiam = 'sahko' THEN myymal[4]
		WHEN rak_temp.energiam = 'puu' THEN myymal[5]
		WHEN rak_temp.energiam = 'maalampo' THEN myymal[6]
		ELSE 0 END),0)::int
	as myymal_ala,
	NULLIF(COALESCE(rak_temp.majoit_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN majoit[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN majoit[2]
		WHEN rak_temp.energiam = 'kaasu' THEN majoit[3]
		WHEN rak_temp.energiam = 'sahko' THEN majoit[4]
		WHEN rak_temp.energiam = 'puu' THEN majoit[5]
		WHEN rak_temp.energiam = 'maalampo' THEN majoit[6]
		ELSE 0 END),0)::int
	as majoit_ala,
	NULLIF(COALESCE(rak_temp.asla_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN asla[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN asla[2]
		WHEN rak_temp.energiam = 'kaasu' THEN asla[3]
		WHEN rak_temp.energiam = 'sahko' THEN asla[4]
		WHEN rak_temp.energiam = 'puu' THEN asla[5]
		WHEN rak_temp.energiam = 'maalampo' THEN asla[6]
		ELSE 0 END),0)::int
	as asla_ala,
	NULLIF(COALESCE(rak_temp.ravint_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN ravint[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN ravint[2]
		WHEN rak_temp.energiam = 'kaasu' THEN ravint[3]
		WHEN rak_temp.energiam = 'sahko' THEN ravint[4]
		WHEN rak_temp.energiam = 'puu' THEN ravint[5]
		WHEN rak_temp.energiam = 'maalampo' THEN ravint[6]
		ELSE 0 END),0)::int
	as ravint_ala,
	NULLIF(COALESCE(rak_temp.tsto_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN tsto[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN tsto[2]
		WHEN rak_temp.energiam = 'kaasu' THEN tsto[3]
		WHEN rak_temp.energiam = 'sahko' THEN tsto[4]
		WHEN rak_temp.energiam = 'puu' THEN tsto[5]
		WHEN rak_temp.energiam = 'maalampo' THEN tsto[6]
		ELSE 0 END),0)::int
	as tsto_ala,
	NULLIF(COALESCE(rak_temp.liiken_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN liiken[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN liiken[2]
		WHEN rak_temp.energiam = 'kaasu' THEN liiken[3]
		WHEN rak_temp.energiam = 'sahko' THEN liiken[4]
		WHEN rak_temp.energiam = 'puu' THEN liiken[5]
		WHEN rak_temp.energiam = 'maalampo' THEN liiken[6]
		ELSE 0 END),0)::int
	as liiken_ala,
	NULLIF(COALESCE(rak_temp.hoito_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN hoito[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN hoito[2]
		WHEN rak_temp.energiam = 'kaasu' THEN hoito[3]
		WHEN rak_temp.energiam = 'sahko' THEN hoito[4]
		WHEN rak_temp.energiam = 'puu' THEN hoito[5]
		WHEN rak_temp.energiam = 'maalampo' THEN hoito[6]
		ELSE 0 END),0)::int
	as hoito_ala,
	NULLIF(COALESCE(rak_temp.kokoon_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN kokoon[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN kokoon[2]
		WHEN rak_temp.energiam = 'kaasu' THEN kokoon[3]
		WHEN rak_temp.energiam = 'sahko' THEN kokoon[4]
		WHEN rak_temp.energiam = 'puu' THEN kokoon[5]
		WHEN rak_temp.energiam = 'maalampo' THEN kokoon[6]
		ELSE 0 END),0)::int
	as kokoon_ala,
	NULLIF(COALESCE(rak_temp.opetus_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN opetus[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN opetus[2]
		WHEN rak_temp.energiam = 'kaasu' THEN opetus[3]
		WHEN rak_temp.energiam = 'sahko' THEN opetus[4]
		WHEN rak_temp.energiam = 'puu' THEN opetus[5]
		WHEN rak_temp.energiam = 'maalampo' THEN opetus[6]
		ELSE 0 END),0)::int
	as opetus_ala,
	NULLIF(COALESCE(rak_temp.teoll_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN teoll[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN teoll[2]
		WHEN rak_temp.energiam = 'kaasu' THEN teoll[3]
		WHEN rak_temp.energiam = 'sahko' THEN teoll[4]
		WHEN rak_temp.energiam = 'puu' THEN teoll[5]
		WHEN rak_temp.energiam = 'maalampo' THEN teoll[6]
		ELSE 0 END),0)::int
	as teoll_ala,
	NULLIF(COALESCE(rak_temp.varast_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN varast[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN varast[2]
		WHEN rak_temp.energiam = 'kaasu' THEN varast[3]
		WHEN rak_temp.energiam = 'sahko' THEN varast[4]
		WHEN rak_temp.energiam = 'puu' THEN varast[5]
		WHEN rak_temp.energiam = 'maalampo' THEN varast[6]
		ELSE 0 END),0)::int
	as varast_ala,
	NULLIF(COALESCE(rak_temp.muut_ala, 0) + (CASE
		WHEN rak_temp.energiam = 'kaukolampo' THEN muut[1]
		WHEN rak_temp.energiam = 'kevyt_oljy' THEN muut[2]
		WHEN rak_temp.energiam = 'kaasu' THEN muut[3]
		WHEN rak_temp.energiam = 'sahko' THEN muut[4]
		WHEN rak_temp.energiam = 'puu' THEN muut[5]
		WHEN rak_temp.energiam = 'maalampo' THEN muut[6]
		ELSE 0 END),0)::int
	as muut_ala
FROM rak_temp
LEFT JOIN muutos ON rak_temp.xyind = muutos.xyind AND rak_temp.rakv = muutos.rakv) query
WHERE NOT (query.erpien_ala IS NULL AND query.rivita_ala IS NULL and query.askert_ala IS NULL and query.liike_ala IS NULL and query.tsto_ala IS NULL and query.hoito_ala IS NULL and query.liiken_ala IS NULL AND
	query.kokoon_ala IS NULL and query.opetus_ala IS NULL and query.teoll_ala IS NULL AND query.varast_ala IS NULL AND query.muut_ala IS NULL);

UPDATE rak_new SET asuin_ala = COALESCE(rak_new.erpien_ala,0) + COALESCE(rak_new.rivita_ala,0) + COALESCE(rak_new.askert_ala,0),
rakyht_ala = COALESCE(rak_new.erpien_ala,0) + COALESCE(rak_new.rivita_ala,0) + COALESCE(rak_new.askert_ala,0) + COALESCE(rak_new.liike_ala,0) + COALESCE(rak_new.tsto_ala,0) + COALESCE(rak_new.liiken_ala,0) +
COALESCE(rak_new.hoito_ala,0) + COALESCE(rak_new.kokoon_ala,0) + COALESCE(rak_new.opetus_ala,0) + COALESCE(rak_new.teoll_ala,0) + COALESCE(rak_new.varast_ala,0) + COALESCE(rak_new.muut_ala,0);

RETURN QUERY SELECT * FROM rak_new UNION SELECT * FROM rak WHERE rak.rakv >= 2019;
DROP TABLE IF EXISTS ykr, rak, rak_new, rak_temp, local_jakauma, global_jakauma, kayttotapajakauma;

END;
$$ LANGUAGE plpgsql;