from typing import List
from uuid import UUID

import fastapi
import pydantic

from . import common

router = fastapi.APIRouter()


class Playbook(pydantic.BaseModel):
    name: str


class PlaybookListItem(Playbook):
    id: UUID


@router.get(
    "/playbooks",
    response_model=List[PlaybookListItem],
    summary="List all Playbooks",
)
async def get_playbooks(client=fastapi.Depends(common.get_db_client)):
    return common.JSONTextResponse(
        await client.query_json("select Playbook { id, name }"),
    )


@router.get(
    "/playbooks/{playbook_id}",
    response_model=Playbook,
    responses={404: {"model": common.Error}},
    summary="Retrieve a single Playbook by ID",
)
async def get_playbook(playbook_id: UUID, client=fastapi.Depends(common.get_db_client)):
    return common.JSONTextResponse(
        await client.query_required_single_json(
            "select Playbook { name } filter .id = <uuid>$id", id=playbook_id
        )
    )


@router.post(
    "/playbooks",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_class=fastapi.Response,
    summary="Create a new Playbook",
)
async def add_playbook(
    playbook: Playbook,
    request: fastapi.Request,
    response: fastapi.Response,
    client=fastapi.Depends(common.get_db_client),
):
    playbook = await client.query_required_single(
        "insert Playbook { name := <str>$name }", name=playbook.name
    )
    response.headers["Location"] = request.url_for(
        "get_playbook", playbook_id=playbook.id
    )


@router.put(
    "/playbooks/{playbook_id}",
    status_code=fastapi.status.HTTP_204_NO_CONTENT,
    response_class=fastapi.Response,
    responses={404: {"model": common.Error}},
    summary="Modify the specified Playbook",
)
async def set_playbook(
    playbook: Playbook,
    playbook_id: UUID,
    request: fastapi.Request,
    response: fastapi.Response,
    client=fastapi.Depends(common.get_db_client),
):
    playbook = await client.query_required_single(
        "update Playbook filter .id = <uuid>$id set { name := <str>$name}",
        id=playbook_id,
        name=playbook.name,
    )
    response.headers["Location"] = request.url_for(
        "get_playbook", playbook_id=playbook.id
    )


@router.delete(
    "/playbooks/{playbook_id}",
    status_code=fastapi.status.HTTP_204_NO_CONTENT,
    response_class=fastapi.Response,
    responses={404: {"model": common.Error}},
    summary="Delete the specified Playbook",
)
async def delete_playbook(
    playbook_id: UUID, client=fastapi.Depends(common.get_db_client)
):
    await client.query_required_single(
        "delete Playbook filter .id = <uuid>$id", id=playbook_id
    )


def init_app(app):
    app.include_router(router, tags=["playbook"])
