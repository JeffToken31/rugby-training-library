PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS families (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
 metadata_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metadata_json)));
CREATE TABLE IF NOT EXISTS variants (
 id TEXT PRIMARY KEY, family_id TEXT REFERENCES families(id), title TEXT,
 origin TEXT NOT NULL CHECK(origin IN ('SOURCE','AI_SUGGESTED','COACH')),
 status TEXT NOT NULL DEFAULT 'IMPORTED' CHECK(status IN ('IMPORTED','AI_PARSED','REVIEWED','VALIDATED','REJECTED')),
 parent_variant_id TEXT REFERENCES variants(id),
 parameters_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(parameters_json)),
 validated_by TEXT, validated_at TEXT,
 CHECK(status != 'VALIDATED' OR (validated_by IS NOT NULL AND validated_at IS NOT NULL)));
CREATE TABLE IF NOT EXISTS resources (
 id TEXT PRIMARY KEY, url TEXT, provider_key TEXT, title TEXT, format TEXT,
 metadata_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metadata_json)));
CREATE TABLE IF NOT EXISTS captures (
 id TEXT PRIMARY KEY, resource_id TEXT NOT NULL REFERENCES resources(id),
 collected_at TEXT NOT NULL, final_url TEXT, http_status INTEGER, mime_type TEXT,
 sha256 TEXT, archive_path TEXT, raw_text_path TEXT, extractor_version TEXT,
 retention_note TEXT, metadata_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metadata_json)));
CREATE TABLE IF NOT EXISTS qualifications (
 id TEXT PRIMARY KEY, resource_id TEXT NOT NULL REFERENCES resources(id),
 type TEXT NOT NULL CHECK(type IN ('SESSION_PDF','EXERCISE_PDF','SESSION_VIDEO','EXERCISE_VIDEO','WEB_PAGE','CYCLE','TECHNICAL_DOCUMENT','PEDAGOGICAL_CONTENT','RULES')),
 strategy TEXT, actor TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS occurrences (
 id TEXT PRIMARY KEY, resource_id TEXT NOT NULL REFERENCES resources(id),
 capture_id TEXT REFERENCES captures(id), locator_text TEXT,
 page_start INTEGER CHECK(page_start>=1), page_end INTEGER,
 second_start REAL CHECK(second_start>=0), second_end REAL,
 CHECK(page_end IS NULL OR (page_start IS NOT NULL AND page_end>=page_start)),
 CHECK(second_end IS NULL OR (second_start IS NOT NULL AND second_end>=second_start)));
CREATE TABLE IF NOT EXISTS exercise_sources (
 variant_id TEXT NOT NULL REFERENCES variants(id), occurrence_id TEXT NOT NULL REFERENCES occurrences(id),
 role TEXT NOT NULL, note TEXT, PRIMARY KEY(variant_id,occurrence_id,role));
CREATE TABLE IF NOT EXISTS sessions (
 id TEXT PRIMARY KEY, title TEXT, origin TEXT NOT NULL CHECK(origin IN ('SOURCE','AI_SUGGESTED','COACH')),
 occurrence_id TEXT REFERENCES occurrences(id), cycle_id TEXT,
 parameters_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(parameters_json)));
CREATE TABLE IF NOT EXISTS session_exercises (
 id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
 variant_id TEXT REFERENCES variants(id), position INTEGER NOT NULL CHECK(position>=0),
 kind TEXT NOT NULL CHECK(kind IN ('EXERCISE','BREAK','INSTRUCTION','OTHER')),
 duration_seconds INTEGER CHECK(duration_seconds>0), group_label TEXT,
 parameters_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(parameters_json)),
 CHECK(kind!='EXERCISE' OR variant_id IS NOT NULL));
CREATE TABLE IF NOT EXISTS tags (
 id TEXT PRIMARY KEY, category TEXT NOT NULL, label TEXT NOT NULL, UNIQUE(category,label));
CREATE TABLE IF NOT EXISTS variant_tags (
 variant_id TEXT REFERENCES variants(id), tag_id TEXT REFERENCES tags(id),
 PRIMARY KEY(variant_id,tag_id));
CREATE TABLE IF NOT EXISTS assertions (
 id TEXT PRIMARY KEY, variant_id TEXT NOT NULL REFERENCES variants(id),
 field_path TEXT NOT NULL, value_json TEXT NOT NULL CHECK(json_valid(value_json)),
 origin TEXT NOT NULL CHECK(origin IN ('SOURCE','AI_INFERRED','COACH_VALIDATED')),
 occurrence_id TEXT REFERENCES occurrences(id), actor TEXT NOT NULL, created_at TEXT NOT NULL,
 selected INTEGER NOT NULL DEFAULT 0 CHECK(selected IN (0,1)),
 CHECK(origin!='SOURCE' OR occurrence_id IS NOT NULL));
CREATE UNIQUE INDEX IF NOT EXISTS one_selected_assertion ON assertions(variant_id,field_path) WHERE selected=1;
CREATE TABLE IF NOT EXISTS duplicate_candidates (
 id TEXT PRIMARY KEY, left_id TEXT NOT NULL REFERENCES variants(id),
 right_id TEXT NOT NULL REFERENCES variants(id), score REAL CHECK(score BETWEEN 0 AND 1),
 relation TEXT NOT NULL DEFAULT 'UNDECIDED' CHECK(relation IN ('SAME_FAMILY','SAME_VARIANT','DIFFERENT_VARIANT','DIFFERENT_EXERCISE','UNDECIDED')),
 method_version TEXT NOT NULL, explanation TEXT, decided_by TEXT, decided_at TEXT,
 CHECK(left_id<right_id), UNIQUE(left_id,right_id,method_version));
CREATE TABLE IF NOT EXISTS ingestion_runs (
 id TEXT PRIMARY KEY, resource_id TEXT NOT NULL REFERENCES resources(id),
 capture_id TEXT REFERENCES captures(id), stage TEXT NOT NULL, tool_version TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('PENDING','RUNNING','DONE','FAILED','BLOCKED')),
 started_at TEXT, finished_at TEXT, error TEXT,
 output_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(output_json)));
