"""Tests for schedule rule template CRUD endpoints."""


async def test_rule_template_crud(client, admin, login):
    headers = await login(admin["email"], admin["password"])

    # başta boş
    empty = await client.get("/api/v1/schedule/rule-templates", headers=headers)
    assert empty.status_code == 200
    assert empty.json() == []

    # oluştur
    created = await client.post(
        "/api/v1/schedule/rule-templates",
        json={"name": "Standart", "rules": {"lessons": [], "closedWeekdays": [5, 6]}},
        headers=headers,
    )
    assert created.status_code == 201
    tpl = created.json()
    assert tpl["name"] == "Standart"
    assert tpl["rules"]["closedWeekdays"] == [5, 6]
    tpl_id = tpl["id"]

    # listede görünür
    listed = await client.get("/api/v1/schedule/rule-templates", headers=headers)
    assert [t["id"] for t in listed.json()] == [tpl_id]

    # aynı isim → 409
    dup = await client.post(
        "/api/v1/schedule/rule-templates",
        json={"name": "Standart", "rules": {}},
        headers=headers,
    )
    assert dup.status_code == 409

    # sil → 204, sonra liste boş
    deleted = await client.delete(f"/api/v1/schedule/rule-templates/{tpl_id}", headers=headers)
    assert deleted.status_code == 204
    again = await client.get("/api/v1/schedule/rule-templates", headers=headers)
    assert again.json() == []
