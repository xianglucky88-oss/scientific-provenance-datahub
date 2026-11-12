import sqlite3

from scientific_provenance.pipeline import run_pipeline


def test_stores_artifacts_lineage_and_fingerprint(tmp_path):
    db = tmp_path / "science.sqlite3"
    result = run_pipeline([{
        "run_id": "r1", "dataset_id": "d", "code_revision": "git:1", "parameters": {"x": 1},
        "started_at": "2026-01-01T00:00:00Z", "status": "succeeded",
        "artifacts": [{"name": "out", "uri": "artifact://r1/out", "sha256": "h"}],
    }, {
        "run_id": "r2", "dataset_id": "d", "code_revision": "git:1", "parameters": {"x": 1},
        "started_at": "2026-01-01T01:00:00Z", "status": "succeeded", "parent_run_id": "r1", "artifacts": [],
    }], db)
    assert result["runs"] == 2 and result["distinct_fingerprints"] == 1
    with sqlite3.connect(db) as conn:
        assert conn.execute("select count(*) from lineage").fetchone()[0] == 1
        assert conn.execute("select count(*) from artifacts").fetchone()[0] == 1
