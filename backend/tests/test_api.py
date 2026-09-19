"""End-to-end API tests against a temporary seeded SQLite database."""
import os
import tempfile

import pytest

# Point the app at a throwaway database before importing it.
_TMP_DB = os.path.join(tempfile.gettempdir(), "bhudrishti_test.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import DEMO_PASSWORD, seed  # noqa: E402

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    seed(reset=True)
    yield
    if os.path.exists(_TMP_DB):
        try:
            os.remove(_TMP_DB)
        except PermissionError:
            pass


def auth_headers(email: str, password: str = DEMO_PASSWORD) -> dict:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def planner():
    return auth_headers("r.mehta@bmc.gov.in")


@pytest.fixture
def surveyor():
    return auth_headers("n.iqbal@geosurv.in")


@pytest.fixture
def public_user():
    return auth_headers("a.sharma@example.com")


# ------------------------------------------------------------------ health / auth
def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_register_login_me_logout():
    payload = {
        "name": "Test Officer",
        "email": "test.officer@example.com",
        "password": "StrongPass123",
        "role": "surveyor",
        "organization": "QA Dept",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == payload["email"]
    assert "password" not in body["user"] and "password_hash" not in body["user"]

    token = body["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "surveyor"
    assert me.json()["role_label"] == "Architect / Surveyor"

    assert client.post("/api/auth/logout", headers=headers).status_code == 200


def test_duplicate_registration_conflicts():
    payload = {"name": "Dup User", "email": "r.mehta@bmc.gov.in", "password": "StrongPass123"}
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"]


def test_weak_password_and_bad_email_rejected():
    res = client.post("/api/auth/register", json={"name": "X", "email": "not-an-email", "password": "a"})
    assert res.status_code == 422
    assert res.json()["detail"] == "Validation failed"
    assert len(res.json()["errors"]) >= 2


def test_login_with_wrong_password_fails():
    res = client.post("/api/auth/login", json={"email": "r.mehta@bmc.gov.in", "password": "wrong-pass"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Incorrect email or password"


def test_login_unknown_email_fails_identically():
    res = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever1"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Incorrect email or password"


def test_protected_endpoints_reject_anonymous_and_bad_tokens():
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/overview").status_code == 401
    bad = {"Authorization": "Bearer not.a.real.token"}
    assert client.get("/api/auth/me", headers=bad).status_code == 401


def test_expired_token_rejected():
    import jwt
    from datetime import datetime, timedelta, timezone

    from app.config import settings

    expired = jwt.encode(
        {"sub": "1", "role": "planner", "exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


# ------------------------------------------------------------------ authorization
def test_public_user_cannot_list_users(public_user):
    res = client.get("/api/users", headers=public_user)
    assert res.status_code == 403


def test_planner_can_list_users(planner):
    res = client.get("/api/users", headers=planner)
    assert res.status_code == 200
    assert res.json()["total"] >= 7
    assert all("password_hash" not in row for row in res.json()["items"])


def test_permission_matrix_reflects_role(public_user, planner):
    pub = client.get("/api/users/permissions", headers=public_user).json()
    assert pub["my_nav_access"] == ["explorer", "search", "passport"]
    assert pub["my_default_view"] == "explorer"
    plan = client.get("/api/users/permissions", headers=planner).json()
    assert plan["my_nav_access"] == "all"
    assert len(plan["matrix"]) == 10


def test_public_user_cannot_create_conflict_or_proposal(public_user):
    assert client.post("/api/proposals", headers=public_user, json={
        "infra_type": "metro", "from_building": "lakeview", "to_building": "dbtrade", "depth_m": 5
    }).status_code == 403
    assert client.post("/api/datasets", headers=public_user, files={
        "file": ("x.geojson", b"{}", "application/json")
    }).status_code == 403


def test_owner_masking_by_role(public_user, planner):
    pub = client.get("/api/buildings/lakeview/levels/floor4", headers=public_user).json()
    off = client.get("/api/buildings/lakeview/levels/floor4", headers=planner).json()
    assert pub["owner"] == "A. Sharma (masked)"
    assert off["owner"] == "Anil Sharma"


# ------------------------------------------------------------------ cadastre reads
def test_locality_map(planner):
    res = client.get("/api/locality", headers=planner)
    assert res.status_code == 200
    body = res.json()
    assert len(body["buildings"]) == 3
    assert body["metro"]["path"].startswith("M 20 200")
    assert len(body["metro"]["stations"]) == 2
    assert len(body["parks"]) == 2
    assert len(body["genericBuildings"]) == 4
    slugs = {b["slug"] for b in body["buildings"]}
    assert slugs == {"lakeview", "dbtrade", "mpplaza"}


def test_building_detail_shape(planner):
    res = client.get("/api/buildings/lakeview", headers=planner)
    assert res.status_code == 200
    body = res.json()
    meta = body["meta"]
    # The frontend reads exactly these keys off its building meta objects.
    for key in ("name", "parent", "floors", "basements", "address", "ward", "zone", "surveyNo",
                "lat", "lng", "landUse", "ownershipType", "boundaryDims", "status",
                "validationStatus", "surveyAccuracy", "gnss", "lidarAvailability", "infra"):
        assert key in meta, key
    assert meta["parent"] == "1450A9B7C23456"
    assert meta["floors"] == 5 and meta["basements"] == 2
    for key in ("roads", "metro", "water", "gas", "electricity", "underground"):
        assert key in meta["infra"], key

    assert len(body["levels"]) == 9
    level = body["levels"][0]
    for key in ("code", "label", "tag", "id3d", "type", "elevation", "area", "volume",
                "owner", "source", "confidence", "below", "airspace", "conflict", "h", "colors"):
        assert key in level, key
    assert {"top", "left", "right"} <= set(level["colors"])

    assert body["conflict_summary"]["count"] == 2
    assert body["conflict_summary"]["severity"] == "critical"


def test_unknown_building_404(planner):
    assert client.get("/api/buildings/nope", headers=planner).status_code == 404
    assert client.get("/api/buildings/lakeview/levels/nope", headers=planner).status_code == 404


def test_vertical_stack_bands(planner):
    res = client.get("/api/buildings/lakeview/vertical-stack", headers=planner)
    assert res.status_code == 200
    bands = {b["id"]: b for b in res.json()["bands"]}
    assert set(bands) == {"airspace", "floors", "ground", "road", "underground", "metro", "deep"}
    assert [l["label"] for l in bands["airspace"]["levels"]] == ["Terrace", "Floor 5"]
    assert [l["label"] for l in bands["ground"]["levels"]] == ["Ground Floor"]
    assert [l["label"] for l in bands["underground"]["levels"]] == ["Basement B1", "Basement B2"]
    assert bands["road"]["note"].startswith("Frontage on Main Road")


def test_depth_reference_and_infra_assets(planner):
    depths = client.get("/api/depth-reference", headers=planner).json()
    assert [d["label"] for d in depths][-1] == "Metro Tunnel"
    assets = client.get("/api/infra-assets", headers=planner, params={"kind": "utility"}).json()
    assert {a["name"] for a in assets} == {"Water line", "Sewer line", "Fibre conduit", "Gas line"}
    metro = client.get("/api/infra-assets/metro-corridor", headers=planner).json()
    assert metro["details"]["completion_pct"] == 61


# ------------------------------------------------------------------ search / passport
def test_search_and_filters(planner):
    res = client.get("/api/search", headers=planner, params={"q": "Lakeview"})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 9
    row = body["items"][0]
    for key in ("addr", "parent", "buildingId", "id3d", "status", "conf", "conflict", "date"):
        assert key in row, key

    by_ulpin = client.get("/api/search", headers=planner, params={"q": "1450A9B7C23456"}).json()
    assert by_ulpin["total"] == 9

    verified = client.get("/api/search", headers=planner, params={"verification_status": "Verified"}).json()
    assert verified["total"] > 0
    assert all(r["conf"] >= 90 for r in verified["items"])

    low = client.get("/api/search", headers=planner, params={"verification_status": "Low Confidence"}).json()
    assert all(r["conf"] < 70 for r in low["items"])

    conflicted = client.get("/api/search", headers=planner, params={"conflict": True}).json()
    assert all(r["conflict"] for r in conflicted["items"])

    typed = client.get("/api/search", headers=planner, params={"property_type": "Apartment"}).json()
    assert typed["total"] > 0

    bad = client.get("/api/search", headers=planner, params={"verification_status": "Bogus"})
    assert bad.status_code == 400


def test_search_pagination(planner):
    page1 = client.get("/api/search", headers=planner, params={"page": 1, "page_size": 5}).json()
    page2 = client.get("/api/search", headers=planner, params={"page": 2, "page_size": 5}).json()
    assert len(page1["items"]) == 5
    assert page1["pages"] >= 2
    assert {r["full_id3d"] for r in page1["items"]}.isdisjoint({r["full_id3d"] for r in page2["items"]})


def test_passport_masks_owner_for_public(public_user, planner):
    ulpin = "1450A9B7C23456-BLD-01-LVL-04-UNIT-402"
    pub = client.get(f"/api/passport/{ulpin}", headers=public_user)
    assert pub.status_code == 200
    body = pub.json()
    assert body["rights"]["ownership"] == "A. Sharma (masked)"
    assert body["verification"]["confidence"] == 96
    assert body["geometry"]["area"] == "92.4 m²"
    assert body["identity"]["parent_ulpin"] == "1450A9B7C23456"

    off = client.get(f"/api/passport/{ulpin}", headers=planner).json()
    assert off["rights"]["ownership"] == "Anil Sharma"

    assert client.get("/api/passport/NOPE", headers=planner).status_code == 404


# ------------------------------------------------------------------ conflicts
def test_conflict_list_stats_and_filters(planner):
    body = client.get("/api/conflicts", headers=planner).json()
    assert body["total"] == 9
    row = body["items"][0]
    for key in ("sev", "type", "prop", "bldg", "vol", "status", "officer", "explain", "rule"):
        assert key in row, key
    assert row["sev"] == "critical"  # critical sorts first

    active = client.get("/api/conflicts", headers=planner, params={"active_only": True}).json()
    assert active["total"] == 7

    critical = client.get("/api/conflicts", headers=planner, params={"severity": "critical"}).json()
    assert critical["total"] == 2

    per_building = client.get("/api/conflicts", headers=planner, params={"building": "dbtrade"}).json()
    assert per_building["total"] == 1

    stats = client.get("/api/conflicts/stats", headers=planner).json()
    assert stats["total"] == 9
    assert stats["critical"] == 2
    assert stats["by_severity"]["clear"] == 2
    assert stats["volumes_scanned"] == 23


def test_run_validation(planner):
    res = client.post("/api/conflicts/validate", headers=planner)
    assert res.status_code == 200
    body = res.json()
    assert len(body["stages"]) == 6
    assert body["critical"] == 2
    assert body["volumes_scanned"] == 23
    assert any(s["status"] == "failed" for s in body["stages"])


def test_conflict_crud_and_resolve(planner):
    created = client.post("/api/conflicts", headers=planner, json={
        "severity": "medium",
        "conflict_type": "Test overlap",
        "property_name": "Unit 999",
        "building_floor": "Bldg 01 / L9",
        "overlap_volume": "1.0 m³",
        "explanation": "Synthetic conflict raised by the test suite.",
        "rule": "Rule TEST-01: test rule.",
        "building_slug": "mpplaza",
        "level_code": "f3",
    })
    assert created.status_code == 201, created.text
    cid = created.json()["id"]
    assert created.json()["buildingId"] == "mpplaza"

    # The level and building are now flagged.
    lvl = client.get("/api/buildings/mpplaza/levels/f3", headers=planner).json()
    assert lvl["conflict"] is True

    patched = client.patch(f"/api/conflicts/{cid}", headers=planner, json={"officer": "QA Bot"})
    assert patched.json()["officer"] == "QA Bot"

    resolved = client.post(f"/api/conflicts/{cid}/resolve", headers=planner)
    assert resolved.status_code == 200
    assert resolved.json()["sev"] == "clear"
    assert resolved.json()["status"] == "Resolved"

    # Resolving clears the flag again, and re-resolving conflicts.
    assert client.get("/api/buildings/mpplaza/levels/f3", headers=planner).json()["conflict"] is False
    assert client.post(f"/api/conflicts/{cid}/resolve", headers=planner).status_code == 409

    assert client.delete(f"/api/conflicts/{cid}", headers=planner).status_code == 200
    assert client.get(f"/api/conflicts/{cid}", headers=planner).status_code == 404


# ------------------------------------------------------------------ approvals
def test_approval_board_and_decisions(planner, surveyor):
    board = client.get("/api/approvals/board", headers=planner).json()
    labels = [c["label"] for c in board["columns"]]
    assert labels == [
        "Submitted by Surveyor", "AI Review Complete", "Needs Correction",
        "Under Officer Review", "Approved", "Published",
    ]
    total = sum(len(c["cases"]) for c in board["columns"])
    assert total == 8
    case = next(c for col in board["columns"] for c in col["cases"] if c["title"] == "Apartment 402")
    for key in ("ulpin_3d", "title", "conf", "sla", "conflict"):
        assert key in case, key

    detail = client.get(f"/api/approvals/{case['id']}", headers=planner).json()
    assert len(detail["events"]) == 3

    # Surveyors submit; only planners decide.
    created = client.post("/api/approvals", headers=surveyor, json={
        "ulpin_3d": "1450C7A55D3390-BLD-01-LVL-03-UNIT-303",
        "title": "Unit 303 test case",
        "confidence": 80,
        "building_slug": "mpplaza",
    })
    assert created.status_code == 201
    new_id = created.json()["id"]
    assert client.post(f"/api/approvals/{new_id}/decision", headers=surveyor,
                       json={"action": "approve"}).status_code == 403

    approved = client.post(f"/api/approvals/{new_id}/decision", headers=planner,
                           json={"action": "approve", "note": "Looks good"})
    assert approved.status_code == 200
    assert approved.json()["stage"] == "approved"

    published = client.post(f"/api/approvals/{new_id}/decision", headers=planner,
                            json={"action": "publish"})
    assert published.json()["stage"] == "published"

    # Already-decided cases can't be rejected afterwards.
    assert client.post(f"/api/approvals/{new_id}/decision", headers=planner,
                       json={"action": "reject"}).status_code == 409

    assert client.post(f"/api/approvals/{new_id}/decision", headers=planner,
                       json={"action": "bogus"}).status_code == 422

    assert client.delete(f"/api/approvals/{new_id}", headers=planner).status_code == 200


# ------------------------------------------------------------------ intake / uploads
def test_dataset_list_and_upload(surveyor, planner):
    listing = client.get("/api/datasets", headers=surveyor).json()
    assert listing["total"] == 4
    assert all({"name", "meta", "state"} <= set(d) for d in listing["items"])

    res = client.post(
        "/api/datasets",
        headers=surveyor,
        files={"file": ("ward12_test.geojson", b'{"type":"FeatureCollection","features":[]}', "application/geo+json")},
        data={"building_slug": "mpplaza", "crs": "EPSG:4326"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["kind"] == "geojson"
    assert body["url"].startswith("/uploads/")
    assert body["size_bytes"] > 0
    assert "GeoJSON" in body["meta"]

    # The stored file is actually served back.
    assert client.get(body["url"]).status_code == 200

    rejected = client.post("/api/datasets", headers=surveyor,
                           files={"file": ("virus.exe", b"MZ", "application/octet-stream")})
    assert rejected.status_code == 400
    assert "Unsupported file type" in rejected.json()["detail"]

    assert client.delete(f"/api/datasets/{body['id']}", headers=surveyor).status_code == 200


def test_lidar_upload_creates_floor_segments(surveyor):
    res = client.post(
        "/api/datasets",
        headers=surveyor,
        files={"file": ("mpplaza_pass01.las", b"LASF" + b"\0" * 64, "application/octet-stream")},
        data={"building_slug": "mpplaza"},
    )
    assert res.status_code == 201
    dataset_id = res.json()["id"]
    assert res.json()["state"] == "AI segmentation ready"

    segments = client.get("/api/floor-segments", headers=surveyor,
                          params={"dataset_id": dataset_id}).json()
    assert len(segments) == 6  # one per mpplaza level
    assert {"label", "conf", "note", "review_status"} <= set(segments[0])

    pipeline = client.get(f"/api/datasets/{dataset_id}/pipeline", headers=surveyor).json()
    assert len(pipeline["stages"]) == 6
    assert pipeline["stages"][-1]["status"] == "active"

    patched = client.patch(f"/api/floor-segments/{segments[0]['id']}", headers=surveyor,
                           json={"confidence": 99, "note": "Manually corrected"})
    assert patched.json()["conf"] == 99

    submitted = client.post("/api/floor-segments/submit", headers=surveyor,
                            params={"dataset_id": dataset_id})
    assert submitted.status_code == 200
    assert submitted.json()["submitted"] == 6
    # Nothing left pending -> 404 on a second submit.
    assert client.post("/api/floor-segments/submit", headers=surveyor,
                       params={"dataset_id": dataset_id}).status_code == 404

    client.delete(f"/api/datasets/{dataset_id}", headers=surveyor)


def test_existing_lidar_segments_seeded(surveyor):
    segments = client.get("/api/floor-segments", headers=surveyor,
                          params={"building": "lakeview"}).json()
    labels = [s["label"] for s in segments]
    assert "Basement B2" in labels
    assert any(s["conf"] == 71 for s in segments)


# ------------------------------------------------------------------ planning
def test_proposal_analysis_finds_real_conflicts(planner):
    profiles = client.get("/api/infra-profiles", headers=planner).json()
    assert {p["value"] for p in profiles} == {"metro", "water", "sewer", "gas", "fibre"}

    # 5 m depth passes through Lakeview's Basement B2 (3.0–6.2 m below grade).
    res = client.post("/api/proposals", headers=planner, json={
        "infra_type": "metro", "from_building": "lakeview", "to_building": "dbtrade",
        "width_m": 4, "depth_m": 5,
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["analyzed"] is True
    assert body["route"] == {"x1": 145.0, "y1": 296.0, "x2": 360.0, "y2": 143.0}
    conflicts = body["conflicts"]
    assert len(conflicts) >= 2
    b2 = next(c for c in conflicts if c["level"] == "Basement B2")
    assert b2["severity"] == "critical"
    assert "passes directly through" in b2["explain"]
    assert "UTL-03" in b2["rule"]
    # DB Trade Centre's pier clearance rule fires for metro routes.
    piers = next(c for c in conflicts if c["level"] == "Parcel boundary / piers")
    assert piers["buildingId"] == "dbtrade"
    assert "GEO-02" in piers["rule"]

    pid = body["id"]
    # A deep route clears the basements but keeps the metro pier finding.
    deep = client.post(f"/api/proposals/{pid}/analyze", headers=planner, params={"depth_m": 30}).json()
    assert all(c["level"] != "Basement B2" for c in deep["conflicts"])
    assert deep["depth_m"] == 30

    # A deep non-metro route is fully clear.
    clear = client.post("/api/proposals", headers=planner, json={
        "infra_type": "water", "from_building": "lakeview", "to_building": "mpplaza", "depth_m": 25,
    }).json()
    assert clear["conflicts"] == []
    assert clear["status"] == "clear"

    assert client.post("/api/proposals", headers=planner, json={
        "infra_type": "metro", "from_building": "lakeview", "to_building": "lakeview", "depth_m": 5,
    }).status_code == 400
    assert client.post("/api/proposals", headers=planner, json={
        "infra_type": "teleport", "from_building": "lakeview", "to_building": "dbtrade", "depth_m": 5,
    }).status_code == 422
    assert client.post("/api/proposals", headers=planner, json={
        "infra_type": "metro", "from_building": "lakeview", "to_building": "dbtrade", "depth_m": 99,
    }).status_code == 422

    client.delete(f"/api/proposals/{pid}", headers=planner)
    client.delete(f"/api/proposals/{clear['id']}", headers=planner)


def test_proposal_ownership_enforced(planner, surveyor):
    created = client.post("/api/proposals", headers=planner, json={
        "infra_type": "gas", "from_building": "lakeview", "to_building": "mpplaza", "depth_m": 20,
    }).json()
    # Surveyors aren't engineers — they can't create or touch proposals.
    assert client.post("/api/proposals", headers=surveyor, json={
        "infra_type": "gas", "from_building": "lakeview", "to_building": "mpplaza", "depth_m": 20,
    }).status_code == 403
    assert client.delete(f"/api/proposals/{created['id']}", headers=surveyor).status_code == 403
    assert client.delete(f"/api/proposals/{created['id']}", headers=planner).status_code == 200


def test_dig_safe_thresholds(planner):
    assets = client.get("/api/utility/assets", headers=planner).json()
    assert len(assets) == 4

    clear = client.post("/api/utility/dig-safe", headers=planner, json={"depth_m": 2.0}).json()
    assert clear["verdict"] == "clear"

    review = client.post("/api/utility/dig-safe", headers=planner, json={"depth_m": 3.0}).json()
    assert review["verdict"] == "review"
    assert review["conflicting_assets"]

    prohibited = client.post("/api/utility/dig-safe", headers=planner, json={"depth_m": 4.0}).json()
    assert prohibited["verdict"] == "prohibited"
    assert "water line" in prohibited["message"].lower()
    assert prohibited["safety_buffer_m"] == 1.5

    assert client.post("/api/utility/dig-safe", headers=planner, json={"depth_m": 99}).status_code == 422


def test_spatial_query(planner):
    near = client.get("/api/spatial-query", headers=planner,
                      params={"building": "lakeview", "radius_m": 100}).json()
    assert near["count"] == 9  # only Lakeview's own volumes
    wide = client.get("/api/spatial-query", headers=planner,
                      params={"building": "lakeview", "radius_m": 500}).json()
    assert wide["count"] > near["count"]
    assert wide["conflicts"] >= 2
    assert wide["results"][0]["distance_m"] == 0.0
    assert client.get("/api/spatial-query", headers=planner,
                      params={"building": "nope", "radius_m": 100}).status_code == 404


# ------------------------------------------------------------------ ULPIN wizard
def test_ulpin_wizard_flow(planner, surveyor):
    config = client.get("/api/ulpin/wizard-config", headers=planner).json()
    assert len(config["steps"]) == 8
    assert "Apartment" in config["unit_types"]

    preview = client.get("/api/ulpin/preview", headers=planner, params={
        "parent_ulpin": "1450A9B7C23456", "level_no": "4", "unit_number": "402",
    }).json()
    assert preview["generated_3d_id"] == "1450A9B7C23456-BLD-01-LVL-04-UNIT-402"

    validation = client.get("/api/ulpin/validate-geometry", headers=planner, params={
        "building": "lakeview", "level_code": "floor4",
    }).json()
    assert validation["conflicts_found"] == 1
    assert validation["passed"] is False
    assert any("fire-escape" in n for n in validation["notes"])

    # 402 already exists -> duplicate 3D ULPIN is refused (Rule ID-01).
    dup = client.post("/api/ulpin/generate", headers=surveyor, json={
        "parent_ulpin": "1450A9B7C23456", "building_slug": "lakeview", "level_code": "floor4",
        "level_no": "4", "unit_type": "Apartment", "unit_number": "402",
    })
    assert dup.status_code == 409
    assert "already exists" in dup.json()["detail"]

    created = client.post("/api/ulpin/generate", headers=surveyor, json={
        "parent_ulpin": "1450A9B7C23456", "building_slug": "lakeview", "level_code": "floor3",
        "level_no": "3", "unit_type": "Apartment", "unit_number": "305",
        "x": 682450.20, "y": 2607330.80, "z": 9.0,
        "ownership": "Individual ownership", "parking_entitlement": "1 bay, Basement B1",
        "common_area_access": "Lift, stair, terrace", "submit_for_approval": True,
    })
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["ids"]["generated_3d_id"] == "1450A9B7C23456-BLD-01-LVL-03-UNIT-305"
    assert body["approval_case_id"] is not None
    assert body["level"]["rights"]["ownership"] == "Individual ownership"

    # It really is in the database and on the approval board.
    fetched = client.get("/api/passport/1450A9B7C23456-BLD-01-LVL-03-UNIT-305", headers=planner)
    assert fetched.status_code == 200
    board = client.get("/api/approvals/board", headers=planner).json()
    titles = [c["title"] for col in board["columns"] for c in col["cases"]]
    assert "Apartment 305" in titles

    # Parent/building mismatch is caught.
    assert client.post("/api/ulpin/generate", headers=surveyor, json={
        "parent_ulpin": "1450A9B7C23456", "building_slug": "mpplaza", "level_code": "f3",
        "level_no": "3", "unit_type": "Apartment", "unit_number": "307",
    }).status_code == 400

    client.delete("/api/buildings/lakeview/levels/floor3-unit-305", headers=planner)
    client.delete(f"/api/approvals/{body['approval_case_id']}", headers=planner)


# ------------------------------------------------------------------ CRUD on cadastre
def test_building_and_level_crud(planner):
    created = client.post("/api/buildings", headers=planner, json={
        "slug": "testblock", "name": "Test Block A", "parcel_ulpin": "1450C7A55D3390",
        "address": "Test Road, MP Nagar", "ward": "Ward 12", "floors": 2, "basements": 1,
        "use_category": "commercial", "map_geometry": {"x": 10, "y": 10, "w": 40, "h": 30},
    })
    assert created.status_code == 201, created.text
    assert created.json()["meta"]["parent"] == "1450C7A55D3390"

    assert client.post("/api/buildings", headers=planner, json={
        "slug": "testblock", "name": "Dup", "parcel_ulpin": "1450C7A55D3390", "address": "X Road",
    }).status_code == 409
    assert client.post("/api/buildings", headers=planner, json={
        "slug": "otherblock", "name": "No Parcel", "parcel_ulpin": "0000NOPE", "address": "X Road",
    }).status_code == 404
    assert client.post("/api/buildings", headers=planner, json={
        "slug": "Bad Slug!", "name": "Bad", "parcel_ulpin": "1450C7A55D3390", "address": "X Road",
    }).status_code == 422

    patched = client.patch("/api/buildings/testblock", headers=planner,
                           json={"name": "Test Block A1", "floors": 3})
    assert patched.json()["meta"]["name"] == "Test Block A1"
    assert patched.json()["meta"]["floors"] == 3

    level = client.post("/api/buildings/testblock/levels", headers=planner, json={
        "code": "gf", "label": "Ground Floor", "tag": "G", "property_type": "Retail",
        "elevation": "0.0 m – 3.0 m", "elevation_min": 0.0, "elevation_max": 3.0,
        "area": "300 m²", "confidence": 75, "colors": {"top": "#ccc", "left": "#bbb", "right": "#aaa"},
    })
    assert level.status_code == 201, level.text
    assert level.json()["id3d"] == "1450C7A55D3390-BLD-01-LVL-GF"

    assert client.post("/api/buildings/testblock/levels", headers=planner, json={
        "code": "gf", "label": "Dup", "tag": "G", "property_type": "Retail", "elevation": "0-3",
    }).status_code == 409
    assert client.post("/api/buildings/testblock/levels", headers=planner, json={
        "code": "x", "label": "Bad confidence", "tag": "X", "property_type": "Retail",
        "elevation": "0-3", "confidence": 500,
    }).status_code == 422

    updated = client.patch("/api/buildings/testblock/levels/gf", headers=planner,
                           json={"confidence": 95, "has_conflict": True})
    assert updated.json()["confidence"] == 95
    assert client.get("/api/buildings/testblock", headers=planner).json()["meta"]["conflict"] is True

    assert client.delete("/api/buildings/testblock/levels/gf", headers=planner).status_code == 200
    assert client.delete("/api/buildings/testblock", headers=planner).status_code == 200
    assert client.get("/api/buildings/testblock", headers=planner).status_code == 404


def test_user_admin_crud(planner):
    created = client.post("/api/users", headers=planner, json={
        "name": "Temp Admin", "email": "temp.admin@example.com", "password": "StrongPass123",
        "role": "constructor", "organization": "Temp Co",
    })
    assert created.status_code == 201
    uid = created.json()["id"]
    assert "password_hash" not in created.json()

    patched = client.patch(f"/api/users/{uid}", headers=planner, json={"role": "surveyor", "is_active": False})
    assert patched.json()["role"] == "surveyor"
    assert patched.json()["is_active"] is False

    # A deactivated account can no longer log in.
    assert client.post("/api/auth/login", json={
        "email": "temp.admin@example.com", "password": "StrongPass123"
    }).status_code == 403

    me = client.get("/api/auth/me", headers=planner).json()
    assert client.patch(f"/api/users/{me['id']}", headers=planner,
                        json={"is_active": False}).status_code == 400
    assert client.delete(f"/api/users/{me['id']}", headers=planner).status_code == 400

    assert client.delete(f"/api/users/{uid}", headers=planner).status_code == 200
    assert client.get(f"/api/users/{uid}", headers=planner).status_code == 404


def test_profile_self_update():
    headers = auth_headers("k.nair@bmrc.co.in")
    res = client.patch("/api/auth/me", headers=headers, json={"organization": "BMRC Phase 2"})
    assert res.json()["organization"] == "BMRC Phase 2"
    changed = client.patch("/api/auth/me", headers=headers, json={"password": "NewStrongPass1"})
    assert changed.status_code == 200
    assert client.post("/api/auth/login", json={
        "email": "k.nair@bmrc.co.in", "password": "NewStrongPass1"
    }).status_code == 200


# ------------------------------------------------------------------ insights / settings
def test_overview_dashboard(planner):
    body = client.get("/api/overview", headers=planner).json()
    labels = {k["label"]: k["value"] for k in body["kpis"]}
    assert labels["Total Parcels"] == "3"
    assert labels["Total Buildings"] == "3"
    assert int(labels["Critical Conflicts"]) == 2
    assert len(body["recent_conflicts"]) == 3
    assert body["recent_conflicts"][0]["sev"] == "critical"
    assert len(body["recent_datasets"]) == 3
    assert len(body["recent_properties"]) == 3
    assert body["active_projects"]
    assert body["activity"] and {"t", "time", "c"} <= set(body["activity"][0])
    assert sum(c["pct"] for c in body["confidence_summary"]) == pytest.approx(100, abs=2)


def test_analytics_and_reports(planner):
    body = client.get("/api/analytics", headers=planner).json()
    assert len(body["kpis"]) == 8
    assert body["ward_conflicts"]
    assert body["priority_queue"]
    assert len(body["confidence_distribution"]) == 3
    assert len(body["dilrmp"]) == 3

    reports = client.get("/api/reports", headers=planner).json()
    assert len(reports) == 8
    assert {"name", "desc", "formats"} <= set(reports[0])

    export = client.get("/api/reports/Conflict Validation Report/export", headers=planner,
                        params={"fmt": "CSV"}).json()
    assert export["row_counts"]["conflicts"] >= 9
    assert client.get("/api/reports/Nope/export", headers=planner).status_code == 404
    assert client.get("/api/reports/Survey Confidence Report/export", headers=planner,
                      params={"fmt": "PDF"}).status_code == 400


def test_settings_endpoints(planner):
    body = client.get("/api/settings", headers=planner).json()
    assert "Bhopal Municipal Area — Ward 12" in body["jurisdictions"]
    assert len(body["role_permissions"]) == 4

    ladm = client.get("/api/settings/ladm-mapping", headers=planner).json()
    assert len(ladm) == 6
    assert ladm[0]["ladm"] == "LA_SpatialUnit"

    legacy = client.get("/api/settings/legacy-mapping", headers=planner).json()
    assert len(legacy) == 3
    assert any(r["khasra"] == "245/2, Ward 12" for r in legacy)
    assert all("volumes" in r for r in legacy)


def test_activity_feed_records_real_actions(planner):
    before = client.get("/api/activity", headers=planner, params={"limit": 50}).json()
    client.post("/api/conflicts/validate", headers=planner)
    after = client.get("/api/activity", headers=planner, params={"limit": 50}).json()
    assert len(after) > len(before)
    assert "Validation run completed" in after[0]["t"]


def test_cors_allows_frontend_origin():
    res = client.options("/api/auth/login", headers={
        "Origin": "http://localhost:5500",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "http://localhost:5500"
    assert res.headers["access-control-allow-credentials"] == "true"
