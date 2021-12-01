import random
import string
import uuid

import pytest

pytestmark = pytest.mark.anyio


def get_id(resp):
    prefix, _, pid = resp.headers["location"].rpartition("/")
    assert prefix == "http://test/playbooks"
    return uuid.UUID(pid)


def gen_name(length):
    return "".join(random.choice(string.printable) for _ in range(length))


async def new(client, *, name):
    resp = await client.post("/playbooks", json={"name": name})
    assert resp.status_code == 201
    pid = get_id(resp)

    resp = await client.get(f"/playbooks/{pid}")
    assert resp.status_code == 200
    assert resp.json() == {"name": name}

    return pid, name


async def get(client):
    resp = await client.get("/playbooks")
    assert resp.status_code == 200
    return resp.json()


async def test_crud(client):
    assert await get(client) == []

    name = gen_name(9)
    name2 = gen_name(10)
    pid, name = await new(client, name=name)
    pid2, name2 = await new(client, name=name2)
    assert pid != pid2
    assert name != name2

    non_exist_pid = uuid.uuid4()
    assert pid != non_exist_pid
    resp = await client.get(f"/playbooks/{non_exist_pid}")
    assert resp.status_code == 404
    resp = await client.delete(f"/playbooks/{non_exist_pid}")
    assert resp.status_code == 404

    playbooks = await get(client)
    assert {"id": str(pid), "name": name} in playbooks
    assert {"id": str(pid2), "name": name2} in playbooks

    new_name = gen_name(11)
    assert new_name != name
    resp = await client.put(f"/playbooks/{pid}", json={"name": new_name})
    assert resp.status_code == 204
    assert get_id(resp) == pid

    playbooks = await get(client)
    assert {"id": str(pid), "name": new_name} in playbooks
    assert {"id": str(pid2), "name": name2} in playbooks

    resp = await client.delete(f"/playbooks/{pid}")
    assert resp.status_code == 204

    assert await get(client) == [{"id": str(pid2), "name": name2}]

    resp = await client.delete(f"/playbooks/{pid}")
    assert resp.status_code == 404
