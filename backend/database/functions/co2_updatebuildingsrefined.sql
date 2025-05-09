CREATE SCHEMA IF NOT EXISTS functions;
DROP FUNCTION IF EXISTS functions.CO2_UpdateBuildingsRefined;
CREATE OR REPLACE FUNCTION
functions.CO2_UpdateBuildingsRefined(
    rak_taulu regclass,
    ykr_taulu regclass,
    calculationYear integer, -- [year based on which emission values are calculated, min, max calculation years]
    baseYear int,
	targetYear int,
    kehitysskenaario varchar -- PEIKKOn mukainen kehitysskenaario
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
		myymal_hyper_ala int,
		myymal_super_ala int,
		myymal_pien_ala int,
		myymal_muu_ala int,
    majoit_ala int,
    asla_ala int,
    ravint_ala int,
    tsto_ala int,
    liiken_ala int,
    hoito_ala int,
    kokoon_ala int,
    opetus_ala int,
    teoll_ala int,
		teoll_kaivos_ala int,
		teoll_elint_ala int,
		teoll_tekst_ala int,
		teoll_puu_ala int,
		teoll_paper_ala int,
		teoll_kemia_ala int,
		teoll_miner_ala int,
		teoll_mjalos_ala int,
		teoll_metal_ala int,
		teoll_kone_ala int,
		teoll_muu_ala int,
		teoll_energ_ala int,
		teoll_vesi_ala int,
		teoll_yhdysk_ala int,
    varast_ala int,
    muut_ala int
) AS $$
DECLARE
	defaultdemolition boolean;
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

EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS ykr AS SELECT xyind::varchar, zone, k_ap_ala, k_ar_ala, k_ak_ala, k_muu_ala, k_poistuma FROM %s WHERE (k_ap_ala IS NOT NULL AND k_ap_ala != 0) OR (k_ar_ala IS NOT NULL AND k_ar_ala != 0) OR (k_ak_ala IS NOT NULL AND k_ak_ala != 0) OR (k_muu_ala IS NOT NULL AND k_muu_ala != 0) OR (k_poistuma IS NOT NULL AND k_poistuma != 0)', ykr_taulu);
EXECUTE format('CREATE TEMP TABLE IF NOT EXISTS rak AS SELECT xyind::varchar, rakv::int, energiam, rakyht_ala :: int, asuin_ala :: int, erpien_ala :: int, rivita_ala :: int, askert_ala :: int, liike_ala :: int, myymal_ala :: int, myymal_hyper_ala :: int, myymal_super_ala :: int, myymal_pien_ala :: int, myymal_muu_ala :: int, majoit_ala :: int, asla_ala :: int, ravint_ala :: int, tsto_ala :: int, liiken_ala :: int, hoito_ala :: int, kokoon_ala :: int, opetus_ala :: int, teoll_ala :: int, teoll_kaivos_ala :: int, teoll_elint_ala :: int, teoll_tekst_ala :: int, teoll_puu_ala :: int, teoll_paper_ala :: int, teoll_kemia_ala :: int, teoll_miner_ala :: int, teoll_mjalos_ala :: int, teoll_metal_ala :: int, teoll_kone_ala :: int, teoll_muu_ala :: int, teoll_energ_ala :: int, teoll_vesi_ala :: int, teoll_yhdysk_ala :: int, varast_ala :: int, muut_ala :: int FROM %s WHERE rakv::int != 0', rak_taulu);

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

/* Puretaan rakennuksia  */
/* Demolishing buildings */
SELECT CASE WHEN k_poistuma > 999998 AND k_poistuma < 1000000 THEN true ELSE false END FROM ykr LIMIT 1 INTO defaultdemolition;

UPDATE rak b SET
    erpien_ala = GREATEST(b.erpien_ala - erpien, 0),
    rivita_ala = GREATEST(b.rivita_ala - rivita, 0),
    askert_ala = GREATEST(b.askert_ala - askert, 0),
    liike_ala = GREATEST(b.liike_ala - liike, 0),
    myymal_ala = GREATEST(b.myymal_ala - myymal, 0),
	    myymal_hyper_ala = GREATEST(b.myymal_hyper_ala - myy_hyper, 0),
		myymal_super_ala = GREATEST(b.myymal_super_ala - myy_super, 0),
		myymal_pien_ala = GREATEST(b.myymal_pien_ala - myy_pien, 0),
		myymal_muu_ala = GREATEST(b.myymal_muu_ala - myy_muu, 0),
    majoit_ala = GREATEST(b.majoit_ala - majoit, 0),
    asla_ala = GREATEST(b.asla_ala - asla, 0),
    ravint_ala = GREATEST(b.ravint_ala - ravint, 0),
    tsto_ala = GREATEST(b.tsto_ala - tsto, 0),
    liiken_ala = GREATEST(b.liiken_ala - liiken, 0),
    hoito_ala = GREATEST(b.hoito_ala - hoito, 0),
    kokoon_ala = GREATEST(b.kokoon_ala - kokoon, 0),
    opetus_ala = GREATEST(b.opetus_ala - opetus, 0),
    teoll_ala = GREATEST(b.teoll_ala - teoll, 0),
	    teoll_kaivos_ala = GREATEST(b.teoll_kaivos_ala - teoll_kaivos, 0),
		teoll_elint_ala = GREATEST(b.teoll_elint_ala - teoll_elint, 0),
	    teoll_tekst_ala = GREATEST(b.teoll_tekst_ala - teoll_tekst, 0),
	    teoll_puu_ala = GREATEST(b.teoll_puu_ala - teoll_puu, 0),
	    teoll_paper_ala = GREATEST(b.teoll_paper_ala - teoll_paper, 0),
	    teoll_kemia_ala = GREATEST(b.teoll_kemia_ala - teoll_kemia, 0),
	    teoll_miner_ala = GREATEST(b.teoll_miner_ala - teoll_miner, 0),
		teoll_mjalos_ala = GREATEST(b.teoll_mjalos_ala - teoll_mjalos, 0),
		teoll_metal_ala = GREATEST(b.teoll_metal_ala - teoll_metal, 0),
		teoll_kone_ala = GREATEST(b.teoll_kone_ala - teoll_kone, 0),
		teoll_muu_ala = GREATEST(b.teoll_muu_ala - teoll_muu, 0),
		teoll_energ_ala = GREATEST(b.teoll_energ_ala - teoll_energ, 0),
		teoll_vesi_ala = GREATEST(b.teoll_vesi_ala - teoll_vesi, 0),
		teoll_yhdysk_ala = GREATEST(b.teoll_yhdysk_ala - teoll_yhdysk, 0),
    varast_ala = GREATEST(b.varast_ala - varast, 0),
    muut_ala = GREATEST(b.muut_ala - muut, 0)
FROM (
WITH poistuma AS (
    SELECT ykr.xyind, (CASE WHEN defaultdemolition = TRUE THEN 0.0015 ELSE SUM(k_poistuma) END) AS poistuma FROM ykr GROUP BY ykr.xyind
),
buildings AS (
	SELECT rak.xyind, rak.rakv,
		CASE WHEN defaultdemolition = TRUE THEN rak.erpien_ala :: real ELSE rak.erpien_ala :: real / NULLIF(grouped.rakyht_ala, 0) END erpien,
		CASE WHEN defaultdemolition = TRUE THEN rak.rivita_ala :: real ELSE rak.rivita_ala :: real / NULLIF(grouped.rakyht_ala, 0) END rivita,
		CASE WHEN defaultdemolition = TRUE THEN rak.askert_ala :: real ELSE rak.askert_ala :: real / NULLIF(grouped.rakyht_ala, 0) END askert,
		CASE WHEN defaultdemolition = TRUE THEN rak.liike_ala :: real ELSE rak.liike_ala :: real / NULLIF(grouped.rakyht_ala, 0) END liike,
        CASE WHEN defaultdemolition = TRUE THEN rak.myymal_ala :: real ELSE rak.myymal_ala :: real / NULLIF(grouped.rakyht_ala, 0) END myymal,
			CASE WHEN defaultdemolition = TRUE THEN rak.myymal_hyper_ala :: real ELSE rak.myymal_hyper_ala :: real / NULLIF(grouped.rakyht_ala, 0) END myy_hyper,
			CASE WHEN defaultdemolition = TRUE THEN rak.myymal_super_ala :: real ELSE rak.myymal_super_ala :: real / NULLIF(grouped.rakyht_ala, 0) END myy_super,
			CASE WHEN defaultdemolition = TRUE THEN rak.myymal_pien_ala :: real ELSE rak.myymal_pien_ala :: real / NULLIF(grouped.rakyht_ala, 0) END myy_pien,
			CASE WHEN defaultdemolition = TRUE THEN rak.myymal_muu_ala :: real ELSE rak.myymal_muu_ala :: real / NULLIF(grouped.rakyht_ala, 0) END myy_muu,
		CASE WHEN defaultdemolition = TRUE THEN rak.majoit_ala :: real ELSE rak.majoit_ala :: real / NULLIF(grouped.rakyht_ala, 0) END majoit,
        CASE WHEN defaultdemolition = TRUE THEN rak.asla_ala :: real ELSE rak.asla_ala :: real / NULLIF(grouped.rakyht_ala, 0) END asla,
        CASE WHEN defaultdemolition = TRUE THEN rak.ravint_ala :: real ELSE rak.ravint_ala :: real / NULLIF(grouped.rakyht_ala, 0) END ravint,
		CASE WHEN defaultdemolition = TRUE THEN rak.tsto_ala :: real ELSE rak.tsto_ala :: real / NULLIF(grouped.rakyht_ala, 0) END tsto,
		CASE WHEN defaultdemolition = TRUE THEN rak.liiken_ala :: real ELSE rak.liiken_ala :: real / NULLIF(grouped.rakyht_ala, 0) END liiken,
		CASE WHEN defaultdemolition = TRUE THEN rak.hoito_ala :: real ELSE rak.hoito_ala :: real / NULLIF(grouped.rakyht_ala, 0) END hoito,
		CASE WHEN defaultdemolition = TRUE THEN rak.kokoon_ala :: real ELSE rak.kokoon_ala :: real / NULLIF(grouped.rakyht_ala, 0) END kokoon,
		CASE WHEN defaultdemolition = TRUE THEN rak.opetus_ala :: real ELSE rak.opetus_ala :: real / NULLIF(grouped.rakyht_ala, 0) END opetus,
		CASE WHEN defaultdemolition = TRUE THEN rak.teoll_ala :: real ELSE rak.teoll_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll,
			CASE WHEN defaultdemolition = TRUE THEN rak.teoll_kaivos_ala :: real ELSE rak.teoll_kaivos_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_kaivos,
			CASE WHEN defaultdemolition = TRUE THEN rak.teoll_elint_ala :: real ELSE rak.teoll_elint_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_elint,	
			CASE WHEN defaultdemolition = TRUE THEN rak.teoll_tekst_ala :: real ELSE rak.teoll_tekst_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_tekst,
			CASE WHEN defaultdemolition = TRUE THEN rak.teoll_puu_ala :: real ELSE rak.teoll_puu_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_puu,
			CASE WHEN defaultdemolition = TRUE THEN rak.teoll_paper_ala :: real ELSE rak.teoll_paper_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_paper,
			CASE WHEN defaultdemolition = TRUE THEN rak.teoll_kemia_ala :: real ELSE rak.teoll_kemia_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_kemia,
			CASE WHEN defaultdemolition = TRUE THEN rak.teoll_miner_ala :: real ELSE rak.teoll_miner_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_miner,
			CASE WHEN defaultdemolition = TRUE THEN rak.teoll_mjalos_ala :: real ELSE rak.teoll_mjalos_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_mjalos,
			CASE WHEN defaultdemolition = TRUE THEN rak.teoll_metal_ala :: real ELSE rak.teoll_metal_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_metal,
			CASE WHEN defaultdemolition = TRUE THEN rak.teoll_kone_ala :: real ELSE rak.teoll_kone_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_kone,
			CASE WHEN defaultdemolition = TRUE THEN rak.teoll_muu_ala :: real ELSE rak.teoll_muu_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_muu,
			CASE WHEN defaultdemolition = TRUE THEN rak.teoll_energ_ala :: real ELSE rak.teoll_energ_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_energ,
			CASE WHEN defaultdemolition = TRUE THEN rak.teoll_vesi_ala :: real ELSE rak.teoll_vesi_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_vesi,
			CASE WHEN defaultdemolition = TRUE THEN rak.teoll_yhdysk_ala :: real ELSE rak.teoll_yhdysk_ala :: real / NULLIF(grouped.rakyht_ala, 0) END teoll_yhdysk,
		CASE WHEN defaultdemolition = TRUE THEN rak.varast_ala :: real ELSE rak.varast_ala:: real / NULLIF(grouped.rakyht_ala, 0) END varast,
		CASE WHEN defaultdemolition = TRUE THEN rak.muut_ala :: real ELSE rak.muut_ala :: real / NULLIF(grouped.rakyht_ala, 0) END muut
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
		poistuma * myy_hyper myy_hyper,
		poistuma * myy_super myy_super,
		poistuma * myy_pien myy_pien,
		poistuma * myy_muu myy_muu,
	poistuma * majoit majoit,
	poistuma * asla asla,
	poistuma * ravint ravint,
	poistuma * tsto tsto,
	poistuma * liiken liiken,
	poistuma * hoito hoito,
	poistuma * kokoon kokoon,
	poistuma * opetus opetus,
	poistuma * teoll teoll,
		poistuma * teoll_kaivos teoll_kaivos,
		poistuma * teoll_elint teoll_elint,	
		poistuma * teoll_tekst teoll_tekst,
		poistuma * teoll_puu teoll_puu,
		poistuma * teoll_paper teoll_paper,
		poistuma * teoll_kemia teoll_kemia,
		poistuma * teoll_miner teoll_miner,
		poistuma * teoll_mjalos teoll_mjalos,
		poistuma * teoll_metal teoll_metal,
		poistuma * teoll_kone teoll_kone,
		poistuma * teoll_muu teoll_muu,
		poistuma * teoll_energ teoll_energ,
		poistuma * teoll_vesi teoll_vesi,
		poistuma * teoll_yhdysk teoll_yhdysk,
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

/* Lasketaan myös vakiokäyttötapausjakaumat uusia alueita varten */
/* Käyttöalaperusteinen käyttötapajakauma generoidaan rakennusdatasta UZ-vyöhykkeittäin */
/* Calculate default proportions of building usage for new areas as well */
CREATE TEMP TABLE IF NOT EXISTS kayttotapajakauma AS 
SELECT ykr.zone,
	COALESCE(SUM(r.liike_ala)::real  / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as liike_osuus,
	COALESCE(SUM(r.myymal_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as myymal_osuus,
	COALESCE(SUM(r.majoit_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as majoit_osuus,
	COALESCE(SUM(r.asla_ala)::real   / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as asla_osuus,
	COALESCE(SUM(r.ravint_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as ravint_osuus,
	COALESCE(SUM(r.tsto_ala)::real   / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as tsto_osuus,
	COALESCE(SUM(r.liiken_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as liiken_osuus,
	COALESCE(SUM(r.hoito_ala)::real  / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as hoito_osuus,
	COALESCE(SUM(r.kokoon_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as kokoon_osuus,
	COALESCE(SUM(r.opetus_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as opetus_osuus,
	COALESCE(SUM(r.teoll_ala)::real  / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as teoll_osuus,
	COALESCE(SUM(r.varast_ala)::real / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as varast_osuus,
	COALESCE(SUM(r.muut_ala)::real   / NULLIF(SUM(r.liike_ala) + SUM(r.tsto_ala) + SUM(r.liiken_ala) + SUM(r.hoito_ala) + SUM(r.kokoon_ala) + SUM(r.opetus_ala) + SUM(r.teoll_ala) + SUM(r.varast_ala) + SUM(r.muut_ala),0),0) as muut_osuus
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

/* Laskenta tehdään vain 2000-luvulta eteenpäin rakennetuille tai rakennettaville rakennuksille */
/* Lasketaan nykyisen paikallisesta rakennusdatasta muodostetun ruutuaineiston mukainen ruutukohtainen energiajakauma rakennustyypeittäin */
/* Laskenta tehdään vain 2000-luvulta eteenpäin rakennetuille tai rakennettaville rakennuksille */
CREATE TEMP TABLE IF NOT EXISTS local_jakauma AS
WITH kaukolampo AS (
    SELECT
		SUM(rak.rakyht_ala) as rakyht,
		SUM(rak.erpien_ala) as erpien,
		SUM(rak.rivita_ala) as rivita,
		SUM(rak.askert_ala) as askert,
		SUM(rak.liike_ala) as liike,
		SUM(rak.tsto_ala) as tsto,
		SUM(rak.liiken_ala) as liiken,
		SUM(rak.hoito_ala) as hoito,
		SUM(rak.kokoon_ala) as kokoon,
		SUM(rak.opetus_ala) as opetus,
		SUM(rak.teoll_ala) as teoll,
		SUM(rak.varast_ala) as varast,
		SUM(rak.muut_ala) as muut
	FROM rak WHERE rak.energiam='kaukolampo' AND rak.rakv > 2000 
    ), sahko AS (
    SELECT
		SUM(rak.rakyht_ala) as rakyht,
		SUM(rak.erpien_ala) as erpien,
		SUM(rak.rivita_ala) as rivita,
		SUM(rak.askert_ala) as askert, 
		SUM(rak.liike_ala) as liike, 
		SUM(rak.tsto_ala) as tsto, 
		SUM(rak.liiken_ala) as liiken,
		SUM(rak.hoito_ala) as hoito,
		SUM(rak.kokoon_ala) as kokoon,
		SUM(rak.opetus_ala) as opetus,		 
		SUM(rak.teoll_ala) as teoll,
		SUM(rak.varast_ala) as varast,
		SUM(rak.muut_ala) as muut
	FROM rak WHERE rak.energiam='sahko' AND rak.rakv > 2000
    ), puu AS (
    SELECT
		SUM(rak.rakyht_ala) as rakyht,
		SUM(rak.erpien_ala) as erpien,
		SUM(rak.rivita_ala) as rivita,
		SUM(rak.askert_ala) as askert, 
		SUM(rak.liike_ala) as liike, 
		SUM(rak.tsto_ala) as tsto, 
		SUM(rak.liiken_ala) as liiken,
		SUM(rak.hoito_ala) as hoito,
		SUM(rak.kokoon_ala) as kokoon,
		SUM(rak.opetus_ala) as opetus,		 
		SUM(rak.teoll_ala) as teoll,
		SUM(rak.varast_ala) as varast,
		SUM(rak.muut_ala) as muut
	FROM rak WHERE rak.energiam='puu' AND rak.rakv > 2000
    ), maalampo AS (
    SELECT
		SUM(rak.rakyht_ala) as rakyht,
		SUM(rak.erpien_ala) as erpien,
		SUM(rak.rivita_ala) as rivita,
		SUM(rak.askert_ala) as askert, 
		SUM(rak.liike_ala) as liike, 
		SUM(rak.tsto_ala) as tsto, 
		SUM(rak.liiken_ala) as liiken,
		SUM(rak.hoito_ala) as hoito,
		SUM(rak.kokoon_ala) as kokoon,
		SUM(rak.opetus_ala) as opetus,		 
		SUM(rak.teoll_ala) as teoll,
		SUM(rak.varast_ala) as varast,
		SUM(rak.muut_ala) as muut
	FROM rak WHERE rak.energiam='maalampo' AND rak.rakv > 2000
    ), muu_lammitys AS (
    SELECT 
		SUM(rak.rakyht_ala) as rakyht,
		SUM(rak.erpien_ala) as erpien,
		SUM(rak.rivita_ala) as rivita,
		SUM(rak.askert_ala) as askert,
		SUM(rak.liike_ala) as liike,
		SUM(rak.tsto_ala) as tsto,
		SUM(rak.liiken_ala) as liiken,
		SUM(rak.hoito_ala) as hoito,
		SUM(rak.kokoon_ala) as kokoon,
		SUM(rak.opetus_ala) as opetus,
		SUM(rak.teoll_ala) as teoll,
		SUM(rak.varast_ala) as varast,
		SUM(rak.muut_ala) as muut
	FROM rak WHERE rak.energiam='muu_lammitys' AND rak.rakv > 2000
)
	
SELECT 'rakyht' as rakennus_tyyppi,
kaukolampo.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS kaukolampo,
sahko.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS sahko,
puu.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS puu,
maalampo.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS maalampo,
muu_lammitys.rakyht :: float(4)/ NULLIF(COALESCE(kaukolampo.rakyht,0) + COALESCE(sahko.rakyht,0) + COALESCE(puu.rakyht,0) + COALESCE(maalampo.rakyht,0) + COALESCE(muu_lammitys.rakyht,0),0) AS muu_lammitys
FROM kaukolampo, sahko, puu, maalampo, muu_lammitys

UNION
SELECT 'erpien' as rakennus_tyyppi,
kaukolampo.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS kaukolampo,
sahko.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS sahko,
puu.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS puu,
maalampo.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS maalampo,
muu_lammitys.erpien :: float(4)/ NULLIF(COALESCE(kaukolampo.erpien,0) + COALESCE(sahko.erpien,0) + COALESCE(puu.erpien,0) + COALESCE(maalampo.erpien,0) + COALESCE(muu_lammitys.erpien,0),0) AS muu_lammitys
FROM kaukolampo, sahko, puu, maalampo, muu_lammitys

UNION
SELECT 'rivita' as rakennus_tyyppi,
kaukolampo.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS kaukolampo,
sahko.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS sahko,
puu.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS puu,
maalampo.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS maalampo,
muu_lammitys.rivita :: float(4)/ NULLIF(COALESCE(kaukolampo.rivita,0) + COALESCE(sahko.rivita,0) + COALESCE(puu.rivita,0) + COALESCE(maalampo.rivita,0) + COALESCE(muu_lammitys.rivita,0),0) AS muu_lammitys
FROM kaukolampo, sahko, puu, maalampo, muu_lammitys

UNION
SELECT 'askert' as rakennus_tyyppi,
kaukolampo.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS kaukolampo,
sahko.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS sahko,
puu.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS puu,
maalampo.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS maalampo,
muu_lammitys.askert :: float(4)/ NULLIF(COALESCE(kaukolampo.askert,0) + COALESCE(sahko.askert,0) + COALESCE(puu.askert,0) + COALESCE(maalampo.askert,0) + COALESCE(muu_lammitys.askert,0),0) AS muu_lammitys
FROM kaukolampo, sahko, puu, maalampo, muu_lammitys

UNION
SELECT 'liike' as rakennus_tyyppi,
kaukolampo.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS kaukolampo,
sahko.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS sahko,
puu.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS puu,
maalampo.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS maalampo,
muu_lammitys.liike :: float(4)/ NULLIF(COALESCE(kaukolampo.liike,0) + COALESCE(sahko.liike,0) + COALESCE(puu.liike,0) + COALESCE(maalampo.liike,0) + COALESCE(muu_lammitys.liike,0),0) AS muu_lammitys
FROM kaukolampo, sahko, puu, maalampo, muu_lammitys

UNION
SELECT 'tsto' as rakennus_tyyppi,
kaukolampo.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS kaukolampo,
sahko.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS sahko,
puu.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS puu,
maalampo.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS maalampo,
muu_lammitys.tsto :: float(4)/ NULLIF(COALESCE(kaukolampo.tsto,0) + COALESCE(sahko.tsto,0) + COALESCE(puu.tsto,0) + COALESCE(maalampo.tsto,0) + COALESCE(muu_lammitys.tsto,0),0) AS muu_lammitys
FROM kaukolampo, sahko, puu, maalampo, muu_lammitys

UNION 
SELECT 'liiken' as rakennus_tyyppi,
kaukolampo.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS kaukolampo,
sahko.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS sahko,
puu.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS puu,
maalampo.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS maalampo,
muu_lammitys.liiken :: float(4)/ NULLIF(COALESCE(kaukolampo.liiken,0) + COALESCE(sahko.liiken,0) + COALESCE(puu.liiken,0) + COALESCE(maalampo.liiken,0) + COALESCE(muu_lammitys.liiken,0),0) AS muu_lammitys
FROM kaukolampo, sahko, puu, maalampo, muu_lammitys

UNION 
SELECT 'hoito' as rakennus_tyyppi,
kaukolampo.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS kaukolampo,
sahko.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS sahko,
puu.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS puu,
maalampo.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS maalampo,
muu_lammitys.hoito :: float(4)/ NULLIF(COALESCE(kaukolampo.hoito,0) + COALESCE(sahko.hoito,0) + COALESCE(puu.hoito,0) + COALESCE(maalampo.hoito,0) + COALESCE(muu_lammitys.hoito,0),0) AS muu_lammitys
FROM kaukolampo, sahko, puu, maalampo, muu_lammitys

UNION 
SELECT 'kokoon' as rakennus_tyyppi,
kaukolampo.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS kaukolampo,
sahko.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS sahko,
puu.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS puu,
maalampo.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS maalampo,
muu_lammitys.kokoon :: float(4)/ NULLIF(COALESCE(kaukolampo.kokoon,0) + COALESCE(sahko.kokoon,0) + COALESCE(puu.kokoon,0) + COALESCE(maalampo.kokoon,0) + COALESCE(muu_lammitys.kokoon,0),0) AS muu_lammitys
FROM kaukolampo, sahko, puu, maalampo, muu_lammitys

UNION 
SELECT 'opetus' as rakennus_tyyppi,
kaukolampo.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS kaukolampo,
sahko.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS sahko,
puu.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS puu,
maalampo.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS maalampo,
muu_lammitys.opetus :: float(4)/ NULLIF(COALESCE(kaukolampo.opetus,0) + COALESCE(sahko.opetus,0) + COALESCE(puu.opetus,0) + COALESCE(maalampo.opetus,0) + COALESCE(muu_lammitys.opetus,0),0) AS muu_lammitys
FROM kaukolampo, sahko, puu, maalampo, muu_lammitys

UNION 
SELECT 'teoll' as rakennus_tyyppi,
kaukolampo.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS kaukolampo,
sahko.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS sahko,
puu.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS puu,
maalampo.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS maalampo,
muu_lammitys.teoll :: float(4)/ NULLIF(COALESCE(kaukolampo.teoll,0) + COALESCE(sahko.teoll,0) + COALESCE(puu.teoll,0) + COALESCE(maalampo.teoll,0) + COALESCE(muu_lammitys.teoll,0),0) AS muu_lammitys
FROM kaukolampo, sahko, puu, maalampo, muu_lammitys

UNION 
SELECT 'varast' as rakennus_tyyppi,
kaukolampo.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS kaukolampo,
sahko.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS sahko,
puu.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS puu,
maalampo.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS maalampo,
muu_lammitys.varast :: float(4)/ NULLIF(COALESCE(kaukolampo.varast,0) + COALESCE(sahko.varast,0) + COALESCE(puu.varast,0) + COALESCE(maalampo.varast,0) + COALESCE(muu_lammitys.varast,0),0) AS muu_lammitys
FROM kaukolampo, sahko, puu, maalampo, muu_lammitys

UNION
SELECT 'muut' as rakennus_tyyppi,
kaukolampo.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0)  + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS kaukolampo,
sahko.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) +  COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS sahko,
puu.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS puu,
maalampo.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS maalampo,
muu_lammitys.muut :: float(4)/ NULLIF(COALESCE(kaukolampo.muut,0) + COALESCE(sahko.muut,0) + COALESCE(puu.muut,0) + COALESCE(maalampo.muut,0) + COALESCE(muu_lammitys.muut,0),0) AS muu_lammitys
FROM kaukolampo, sahko, puu, maalampo, muu_lammitys;

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

EXECUTE FORMAT('SELECT ARRAY(
	SELECT %1$I::real
	FROM local_jakauma
	ORDER BY rakennus_tyyppi ASC)', energiamuoto) 
INTO energyarray;

    INSERT INTO rak (xyind, rakv, energiam, rakyht_ala, asuin_ala, erpien_ala, rivita_ala, askert_ala, liike_ala, myymal_ala, myymal_hyper_ala, myymal_super_ala, myymal_pien_ala, myymal_muu_ala, majoit_ala, asla_ala, ravint_ala, tsto_ala, liiken_ala, hoito_ala, kokoon_ala, opetus_ala, teoll_ala, teoll_kaivos_ala, teoll_elint_ala, teoll_tekst_ala, teoll_puu_ala, teoll_paper_ala, teoll_kemia_ala, teoll_miner_ala, teoll_mjalos_ala, teoll_metal_ala, teoll_kone_ala, teoll_muu_ala, teoll_energ_ala, teoll_vesi_ala, teoll_yhdysk_ala,varast_ala, muut_ala)
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
    	NULL::int, -- myymal_hyper_ala
		NULL::int, -- myymal_super_ala
		NULL::int, -- myymal_pien_ala
		NULL::int, -- myymal_muu_ala	
        majoit_osuus * k_muu_ala * (energyarray)[5], -- majoit_ala
        asla_osuus * k_muu_ala * (energyarray)[5], -- asla_ala
        ravint_osuus * k_muu_ala * (energyarray)[5], -- ravint_ala
        tsto_osuus * k_muu_ala * (energyarray)[12], -- tsto_ala
        liiken_osuus * k_muu_ala * (energyarray)[6], -- liiken_ala
        hoito_osuus * k_muu_ala * (energyarray)[3], -- hoito_ala
        kokoon_osuus * k_muu_ala * (energyarray)[4], -- kokoon_ala
        opetus_osuus * k_muu_ala * (energyarray)[8], -- opetus_ala
        teoll_osuus * k_muu_ala * (energyarray)[11], -- teoll_ala
			NULL::int, -- teoll_kaivos_ala,
			NULL::int, -- teoll_elint_ala,
			NULL::int, -- teoll_tekst_ala,
			NULL::int, -- teoll_puu_ala,
			NULL::int, -- teoll_paper_ala,
			NULL::int, -- teoll_kemia_ala,
			NULL::int, -- teoll_miner_ala,
			NULL::int, -- teoll_mjalos_ala,
			NULL::int, -- teoll_metal_ala,
			NULL::int, -- teoll_kone_ala,
			NULL::int, -- teoll_muu_ala,
			NULL::int, -- teoll_energ_ala,
			NULL::int, -- teoll_vesi_ala,
			NULL::int, -- teoll_yhdysk_ala,
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

CREATE TEMP TABLE IF NOT EXISTS tol_osuudet AS SELECT
	DISTINCT ON (rak.xyind) rak.xyind,
	COALESCE(SUM(rak.myymal_hyper_ala) / NULLIF(SUM(rak.myymal_ala),0),0) AS myymal_hyper_osuus,
	COALESCE(SUM(rak.myymal_super_ala) / NULLIF(SUM(rak.myymal_ala),0),0) AS myymal_super_osuus,
	COALESCE(SUM(rak.myymal_pien_ala) /  NULLIF(SUM(rak.myymal_ala),0),0) AS myymal_pien_osuus,
	COALESCE(SUM(rak.myymal_muu_ala) /  NULLIF(SUM(rak.myymal_ala),0),0) AS myymal_muu_osuus,
	COALESCE(SUM(rak.teoll_kaivos_ala) /  NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_kaivos_osuus,
	COALESCE(SUM(rak.teoll_elint_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_elint_osuus,
	COALESCE(SUM(rak.teoll_tekst_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_tekst_osuus,
	COALESCE(SUM(rak.teoll_puu_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_puu_osuus,
	COALESCE(SUM(rak.teoll_paper_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_paper_osuus,
	COALESCE(SUM(rak.teoll_kemia_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_kemia_osuus,
	COALESCE(SUM(rak.teoll_miner_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_miner_osuus,
	COALESCE(SUM(rak.teoll_mjalos_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_mjalos_osuus,
	COALESCE(SUM(rak.teoll_metal_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_metal_osuus,
	COALESCE(SUM(rak.teoll_kone_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_kone_osuus,
	COALESCE(SUM(rak.teoll_muu_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_muu_osuus,
	COALESCE(SUM(rak.teoll_energ_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_energ_osuus,
	COALESCE(SUM(rak.teoll_vesi_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_vesi_osuus,
	COALESCE(SUM(rak.teoll_yhdysk_ala) / NULLIF(SUM(rak.teoll_ala),0),0) AS teoll_yhdys_osuus
FROM rak WHERE rak.rakv < calculationYear GROUP BY rak.xyind;

UPDATE rak SET
	myymal_hyper_ala = rak.myymal_ala * COALESCE(tol.myymal_hyper_osuus, 0.065),
	myymal_super_ala = rak.myymal_ala * COALESCE(tol.myymal_super_osuus, 0.075),
	myymal_pien_ala = rak.myymal_ala * COALESCE(tol.myymal_pien_osuus, 0.04),
	myymal_muu_ala = rak.myymal_ala * COALESCE(tol.myymal_muu_osuus, 0.82),
	teoll_kaivos_ala = rak.teoll_ala * COALESCE(tol.teoll_kaivos_osuus, 0),
	teoll_elint_ala = rak.teoll_ala * COALESCE(tol.teoll_elint_osuus, 0.02),
	teoll_tekst_ala = rak.teoll_ala * COALESCE(tol.teoll_tekst_osuus, 0.015),
	teoll_puu_ala = rak.teoll_ala * COALESCE(tol.teoll_puu_osuus, 0.0015),
	teoll_paper_ala = rak.teoll_ala * COALESCE(tol.teoll_paper_osuus, 0.005),
	teoll_kemia_ala = rak.teoll_ala * COALESCE(tol.teoll_kemia_osuus, 0.009),
	teoll_miner_ala = rak.teoll_ala * COALESCE(tol.teoll_miner_osuus, 0.002),
	teoll_mjalos_ala = rak.teoll_ala * COALESCE(tol.teoll_mjalos_osuus, 0.0007),
	teoll_metal_ala = rak.teoll_ala * COALESCE(tol.teoll_metal_osuus, 0.05),
	teoll_kone_ala = rak.teoll_ala * COALESCE(tol.teoll_kone_osuus, 0.115),
	teoll_muu_ala = rak.teoll_ala * COALESCE(tol.teoll_muu_osuus, 0.777),
	teoll_energ_ala = rak.teoll_ala * COALESCE(tol.teoll_energ_osuus, 0.0037),
	teoll_vesi_ala = rak.teoll_ala * COALESCE(tol.teoll_vesi_osuus, 0.0001),
	teoll_yhdysk_ala = rak.teoll_ala * COALESCE(tol.teoll_yhdys_osuus, 0.01)
FROM tol_osuudet tol WHERE rak.rakv = calculationYear AND tol.xyind = rak.xyind;

/* Päivitetään vanhojen pytinkien lämmitysmuodot */
/* Updating heating characteristics of old buildings */

CREATE TEMP TABLE IF NOT EXISTS rak_temp AS
SELECT DISTINCT ON (r.xyind, r.rakv, energiam) r.xyind, r.rakv,
UNNEST(
	CASE WHEN muu_lammitys IS NULL AND kevyt_oljy IS NULL AND kaasu IS NULL THEN
		ARRAY['kaukolampo', 'sahko', 'puu', 'maalampo'] 
	WHEN muu_lammitys IS NULL AND kaasu IS NULL THEN
		ARRAY['kaukolampo', 'kevyt_oljy', 'sahko', 'puu', 'maalampo'] 
	WHEN muu_lammitys IS NULL THEN
		ARRAY['kaukolampo', 'kevyt_oljy', 'kaasu', 'sahko', 'puu', 'maalampo']
	ELSE ARRAY['kaukolampo', 'kevyt_oljy', 'kaasu', 'sahko', 'puu', 'maalampo', 'muu_lammitys'] END
)::varchar AS energiam,
NULL::int AS rakyht_ala,
NULL::int AS asuin_ala,
NULL::int AS erpien_ala,
NULL::int AS rivita_ala,
NULL::int AS askert_ala,
NULL::int AS liike_ala,
NULL::int AS myymal_ala,
	NULL::int AS myymal_hyper_ala,
	NULL::int AS myymal_super_ala,
	NULL::int AS myymal_pien_ala,
	NULL::int AS myymal_muu_ala,
NULL::int AS majoit_ala,
NULL::int AS asla_ala,
NULL::int AS ravint_ala, 
NULL::int AS tsto_ala,
NULL::int AS liiken_ala,
NULL::int AS hoito_ala,
NULL::int AS kokoon_ala,
NULL::int AS opetus_ala,
NULL::int AS teoll_ala,
	NULL::int AS teoll_kaivos_ala,
	NULL::int AS teoll_elint_ala,
	NULL::int AS teoll_tekst_ala,
	NULL::int AS teoll_puu_ala,
	NULL::int AS teoll_paper_ala,
	NULL::int AS teoll_kemia_ala,
	NULL::int AS teoll_miner_ala,
	NULL::int AS teoll_mjalos_ala,
	NULL::int AS teoll_metal_ala,
	NULL::int AS teoll_kone_ala,
	NULL::int AS teoll_muu_ala,
	NULL::int AS teoll_energ_ala,
	NULL::int AS teoll_vesi_ala,
	NULL::int AS teoll_yhdysk_ala,
NULL::int AS varast_ala,
NULL::int AS muut_ala 
FROM rak r
LEFT JOIN 
(WITH
	kaukolampo AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam='kaukolampo'),
	kevyt_oljy AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam IN ('kevyt_oljy', 'raskas_oljy', 'turve', 'hiili')),
	kaasu AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam='kaasu'),
	sahko AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam='sahko'),
	puu AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam='puu'),
	maalampo AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam='maalampo'),
	muu_lammitys AS (SELECT rak.xyind, rak.rakv FROM rak WHERE rak.energiam='muu_lammitys')
SELECT distinct on (r2.xyind, r2.rakv) r2.xyind, r2.rakv,
	kaukolampo, kevyt_oljy, kaasu, sahko, puu, maalampo, muu_lammitys
FROM rak r2
	LEFT JOIN kaukolampo on r2.xyind = kaukolampo.xyind AND r2.rakv = kaukolampo.rakv AND r2.xyind IN (SELECT kaukolampo.xyind FROM kaukolampo) AND r2.rakv IN (SELECT kaukolampo.rakv FROM kaukolampo)
	LEFT JOIN kevyt_oljy on r2.xyind = kevyt_oljy.xyind AND r2.rakv = kevyt_oljy.rakv AND r2.xyind IN (SELECT kevyt_oljy.xyind FROM kevyt_oljy) AND r2.rakv IN (SELECT kevyt_oljy.rakv FROM kevyt_oljy)
	LEFT JOIN kaasu on r2.xyind = kaasu.xyind AND r2.rakv = kaasu.rakv AND r2.xyind IN (SELECT kaasu.xyind FROM kaasu) AND r2.rakv IN (SELECT kaasu.rakv FROM kaasu)
	LEFT JOIN sahko on r2.xyind = sahko.xyind AND r2.rakv = sahko.rakv AND r2.xyind IN (SELECT sahko.xyind FROM sahko) AND r2.rakv IN (SELECT sahko.rakv FROM sahko)
	LEFT JOIN puu on r2.xyind = puu.xyind AND r2.rakv = puu.rakv AND r2.xyind IN (SELECT puu.xyind FROM puu) AND r2.rakv IN (SELECT puu.rakv FROM puu)
	LEFT JOIN maalampo on r2.xyind = maalampo.xyind AND r2.rakv = maalampo.rakv AND r2.xyind IN (SELECT maalampo.xyind FROM maalampo) AND r2.rakv IN (SELECT maalampo.rakv FROM maalampo)
	LEFT JOIN muu_lammitys on r2.xyind = muu_lammitys.xyind AND r2.rakv = muu_lammitys.rakv AND r2.xyind IN (SELECT muu_lammitys.xyind FROM muu_lammitys) AND r2.rakv IN (SELECT muu_lammitys.rakv FROM muu_lammitys)
WHERE r2.rakv < 2019
	) sq 
ON sq.xyind = r.xyind AND sq.rakv = r.rakv where r.rakv < 2019;

UPDATE rak_temp set rakyht_ala = past.rakyht_ala,
	asuin_ala = past.asuin_ala, erpien_ala = past.erpien_ala, rivita_ala = past.rivita_ala, askert_ala = past.askert_ala, liike_ala = past.liike_ala, myymal_ala = past.myymal_ala,
	myymal_hyper_ala = past.myymal_hyper_ala, myymal_super_ala = past.myymal_super_ala, myymal_pien_ala = past.myymal_pien_ala, myymal_muu_ala = past.myymal_muu_ala,
	majoit_ala = past.majoit_ala, asla_ala = past.asla_ala, ravint_ala = past.ravint_ala,  tsto_ala = past.tsto_ala, liiken_ala = past.liiken_ala, hoito_ala = past.hoito_ala, kokoon_ala = past.kokoon_ala,
	opetus_ala = past.opetus_ala, teoll_ala = past.teoll_ala, 
	teoll_kaivos_ala = past.teoll_kaivos_ala, teoll_elint_ala = past.teoll_elint_ala, teoll_tekst_ala = past.teoll_tekst_ala, teoll_puu_ala = past.teoll_puu_ala,
	teoll_paper_ala = past.teoll_paper_ala, teoll_kemia_ala = past.teoll_kemia_ala, teoll_miner_ala = past.teoll_miner_ala, teoll_mjalos_ala = past.teoll_mjalos_ala,
	teoll_metal_ala = past.teoll_metal_ala, teoll_kone_ala = past.teoll_kone_ala, teoll_muu_ala = past.teoll_muu_ala, teoll_energ_ala = past.teoll_energ_ala, 
	teoll_vesi_ala = past.teoll_vesi_ala, teoll_yhdysk_ala = past.teoll_yhdysk_ala,
	varast_ala = past.varast_ala, muut_ala = past.muut_ala
FROM rak past WHERE rak_temp.xyind = past.xyind AND rak_temp.rakv = past.rakv AND rak_temp.energiam = past.energiam;

CREATE TEMP TABLE IF NOT EXISTS rak_new AS 
SELECT * FROM
(WITH
muutos AS (
 SELECT sq.xyind, sq.rakv,
	ARRAY[sum(erpien[1]), sum(erpien[2]), sum(erpien[3]), sum(erpien[4]), sum(erpien[5]), sum(erpien[6]), sum(erpien[7])] as erpien,
	ARRAY[sum(rivita[1]), sum(rivita[2]), sum(rivita[3]), sum(rivita[4]), sum(rivita[5]), sum(rivita[6]), sum(rivita[7])] as rivita,
	ARRAY[sum(askert[1]), sum(askert[2]), sum(askert[3]), sum(askert[4]), sum(askert[5]), sum(askert[6]), sum(askert[7])] as askert,
	ARRAY[sum(liike[1]), sum(liike[2]), sum(liike[3]), sum(liike[4]), sum(liike[5]), sum(liike[6]), sum(liike[7])] as liike,
	ARRAY[sum(myymal[1]), sum(myymal[2]), sum(myymal[3]), sum(myymal[4]), sum(myymal[5]), sum(myymal[6]), sum(myymal[7])] as myymal,
	ARRAY[sum(majoit[1]), sum(majoit[2]), sum(majoit[3]), sum(majoit[4]), sum(majoit[5]), sum(majoit[6]), sum(majoit[7])] as majoit,
	ARRAY[sum(asla[1]), sum(asla[2]), sum(asla[3]), sum(asla[4]), sum(asla[5]), sum(asla[6]), sum(asla[7])] as asla,
	ARRAY[sum(ravint[1]), sum(ravint[2]), sum(ravint[3]), sum(ravint[4]), sum(ravint[5]), sum(ravint[6]), sum(ravint[7])] as ravint,
	ARRAY[sum(tsto[1]), sum(tsto[2]), sum(tsto[3]), sum(tsto[4]), sum(tsto[5]), sum(tsto[6]), sum(tsto[7])] as tsto,
	ARRAY[sum(liiken[1]), sum(liiken[2]), sum(liiken[3]), sum(liiken[4]), sum(liiken[5]), sum(liiken[6]), sum(liiken[7])] as liiken,
	ARRAY[sum(hoito[1]), sum(hoito[2]), sum(hoito[3]), sum(hoito[4]), sum(hoito[5]), sum(hoito[6]), sum(hoito[7])] as hoito,
	ARRAY[sum(kokoon[1]), sum(kokoon[2]), sum(kokoon[3]), sum(kokoon[4]), sum(kokoon[5]), sum(kokoon[6]), sum(kokoon[7])] as kokoon,
	ARRAY[sum(opetus[1]), sum(opetus[2]), sum(opetus[3]), sum(opetus[4]), sum(opetus[5]), sum(opetus[6]), sum(opetus[7])] as opetus,
	ARRAY[sum(teoll[1]), sum(teoll[2]), sum(teoll[3]), sum(teoll[4]), sum(teoll[5]), sum(teoll[6]), sum(teoll[7])] as teoll,
	ARRAY[sum(varast[1]), sum(varast[2]), sum(varast[3]), sum(varast[4]), sum(varast[5]), sum(varast[6]), sum(varast[7])] as varast,
	ARRAY[sum(muut[1]), sum(muut[2]), sum(muut[3]), sum(muut[4]), sum(muut[5]), sum(muut[6]), sum(muut[7])] as muut
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
	NULL::int AS myymal_hyper_ala,
	NULL::int AS myymal_super_ala,
	NULL::int AS myymal_pien_ala,
	NULL::int AS myymal_muu_ala,
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
	NULL::int AS teoll_kaivos_ala,
	NULL::int AS teoll_elint_ala,
	NULL::int AS teoll_tekst_ala,
	NULL::int AS teoll_puu_ala,
	NULL::int AS teoll_paper_ala,
	NULL::int AS teoll_kemia_ala,
	NULL::int AS teoll_miner_ala,
	NULL::int AS teoll_mjalos_ala,
	NULL::int AS teoll_metal_ala,
	NULL::int AS teoll_kone_ala,
	NULL::int AS teoll_muu_ala,
	NULL::int AS teoll_energ_ala,
	NULL::int AS teoll_vesi_ala,
	NULL::int AS teoll_yhdysk_ala,
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

UPDATE rak_new SET
	myymal_hyper_ala = rak_new.myymal_ala * rak.myymal_hyper_ala::real / NULLIF(COALESCE(rak.myymal_hyper_ala,0) + COALESCE(rak.myymal_super_ala,0) + COALESCE(rak.myymal_pien_ala,0) + COALESCE(rak.myymal_muu_ala,0), 0), 
	myymal_super_ala = rak_new.myymal_ala * rak.myymal_super_ala::real / NULLIF(COALESCE(rak.myymal_hyper_ala,0) + COALESCE(rak.myymal_super_ala,0) + COALESCE(rak.myymal_pien_ala,0) + COALESCE(rak.myymal_muu_ala,0), 0),
	myymal_pien_ala = rak_new.myymal_ala * rak.myymal_pien_ala::real / NULLIF(COALESCE(rak.myymal_hyper_ala,0) + COALESCE(rak.myymal_super_ala,0) + COALESCE(rak.myymal_pien_ala,0) + COALESCE(rak.myymal_muu_ala,0), 0),
	myymal_muu_ala = rak_new.myymal_ala * rak.myymal_muu_ala::real / NULLIF(COALESCE(rak.myymal_hyper_ala,0) + COALESCE(rak.myymal_super_ala,0) + COALESCE(rak.myymal_pien_ala,0) + COALESCE(rak.myymal_muu_ala,0), 0),
	teoll_kaivos_ala = rak_new.teoll_ala * rak.teoll_kaivos_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
	teoll_elint_ala = rak_new.teoll_ala * rak.teoll_elint_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
	teoll_tekst_ala = rak_new.teoll_ala * rak.teoll_tekst_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
	teoll_puu_ala = rak_new.teoll_ala * rak.teoll_puu_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
	teoll_paper_ala = rak_new.teoll_ala * rak.teoll_paper_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
	teoll_kemia_ala = rak_new.teoll_ala * rak.teoll_kemia_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
	teoll_miner_ala = rak_new.teoll_ala * rak.teoll_miner_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
	teoll_mjalos_ala = rak_new.teoll_ala * rak.teoll_mjalos_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
	teoll_metal_ala = rak_new.teoll_ala * rak.teoll_metal_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
	teoll_kone_ala = rak_new.teoll_ala * rak.teoll_kone_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
	teoll_muu_ala = rak_new.teoll_ala * rak.teoll_muu_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
	teoll_energ_ala = rak_new.teoll_ala * rak.teoll_energ_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
	teoll_vesi_ala = rak_new.teoll_ala * rak.teoll_vesi_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0),
	teoll_yhdysk_ala = rak_new.teoll_ala * rak.teoll_yhdysk_ala::real / NULLIF(COALESCE(rak.teoll_kaivos_ala, 0) + COALESCE(rak.teoll_elint_ala, 0) + COALESCE(rak.teoll_tekst_ala, 0) + COALESCE(rak.teoll_puu_ala, 0) + COALESCE(rak.teoll_paper_ala, 0) + COALESCE(rak.teoll_kemia_ala, 0) + COALESCE(rak.teoll_miner_ala, 0) + COALESCE(rak.teoll_mjalos_ala, 0) + COALESCE(rak.teoll_metal_ala, 0) + COALESCE(rak.teoll_kone_ala, 0) + COALESCE(rak.teoll_muu_ala, 0) + COALESCE(rak.teoll_energ_ala, 0) + COALESCE(rak.teoll_vesi_ala, 0) + COALESCE(rak.teoll_yhdysk_ala, 0), 0)
FROM rak WHERE rak.xyind = rak_new.xyind AND rak.energiam = rak_new.energiam AND rak.rakv = rak_new.rakv;

UPDATE rak_new SET myymal_muu_ala = rak_new.myymal_ala
	WHERE rak_new.myymal_ala IS NOT NULL AND rak_new.myymal_hyper_ala IS NULL AND rak_new.myymal_super_ala IS NULL AND rak_new.myymal_pien_ala IS NULL AND rak_new.myymal_muu_ala IS NULL;

UPDATE rak SET myymal_muu_ala = rak.myymal_ala
	WHERE rak.myymal_ala IS NOT NULL AND rak.myymal_hyper_ala IS NULL AND rak.myymal_super_ala IS NULL AND rak.myymal_pien_ala IS NULL AND rak.myymal_muu_ala IS NULL;

UPDATE rak_new SET
	teoll_muu_ala = rak_new.teoll_ala WHERE
	(rak_new.teoll_kaivos_ala IS NULL OR rak_new.teoll_kaivos_ala = 0) AND
	(rak_new.teoll_elint_ala IS NULL OR rak_new.teoll_elint_ala = 0) AND
	(rak_new.teoll_tekst_ala IS NULL OR rak_new.teoll_tekst_ala = 0) AND
	(rak_new.teoll_puu_ala IS NULL OR rak_new.teoll_puu_ala = 0) AND
	(rak_new.teoll_paper_ala IS NULL OR rak_new.teoll_paper_ala = 0) AND
	(rak_new.teoll_kemia_ala IS NULL OR rak_new.teoll_kemia_ala = 0) AND
	(rak_new.teoll_miner_ala IS NULL OR rak_new.teoll_miner_ala = 0) AND
	(rak_new.teoll_mjalos_ala IS NULL OR rak_new.teoll_mjalos_ala = 0) AND
	(rak_new.teoll_metal_ala IS NULL OR rak_new.teoll_metal_ala = 0) AND
	(rak_new.teoll_kone_ala IS NULL OR rak_new.teoll_kone_ala = 0) AND
	(rak_new.teoll_energ_ala IS NULL OR rak_new.teoll_energ_ala = 0) AND
	(rak_new.teoll_vesi_ala IS NULL OR rak_new.teoll_vesi_ala = 0) AND
	(rak_new.teoll_yhdysk_ala IS NULL OR rak_new.teoll_yhdysk_ala = 0);

UPDATE rak SET
	teoll_muu_ala = rak.teoll_ala WHERE
	(rak.teoll_kaivos_ala IS NULL OR rak.teoll_kaivos_ala = 0) AND
	(rak.teoll_elint_ala IS NULL OR rak.teoll_elint_ala = 0) AND
	(rak.teoll_tekst_ala IS NULL OR rak.teoll_tekst_ala = 0) AND
	(rak.teoll_puu_ala IS NULL OR rak.teoll_puu_ala = 0) AND
	(rak.teoll_paper_ala IS NULL OR rak.teoll_paper_ala = 0) AND
	(rak.teoll_kemia_ala IS NULL OR rak.teoll_kemia_ala = 0) AND
	(rak.teoll_miner_ala IS NULL OR rak.teoll_miner_ala = 0) AND
	(rak.teoll_mjalos_ala IS NULL OR rak.teoll_mjalos_ala = 0) AND
	(rak.teoll_metal_ala IS NULL OR rak.teoll_metal_ala = 0) AND
	(rak.teoll_kone_ala IS NULL OR rak.teoll_kone_ala = 0) AND
	(rak.teoll_energ_ala IS NULL OR rak.teoll_energ_ala = 0) AND
	(rak.teoll_vesi_ala IS NULL OR rak.teoll_vesi_ala = 0) AND
	(rak.teoll_yhdysk_ala IS NULL OR rak.teoll_yhdysk_ala = 0);

RETURN QUERY SELECT * FROM rak_new UNION SELECT * FROM rak WHERE rak.rakv >= 2019;
DROP TABLE IF EXISTS ykr, rak, rak_new, rak_temp, local_jakauma, global_jakauma, kayttotapajakauma, tol_osuudet;

END;
$$ LANGUAGE plpgsql;