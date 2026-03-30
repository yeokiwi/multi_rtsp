"""Stream CRUD API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(tags=["streams"])


class StreamCreate(BaseModel):
    name: str
    url: str


class StreamUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None


class StreamResponse(BaseModel):
    id: str
    name: str
    url: str


@router.get("/streams")
async def list_streams(request: Request):
    config_mgr = request.app.state.config_mgr
    go2rtc_mgr = request.app.state.go2rtc_mgr

    streams = config_mgr.get_streams()
    go2rtc_status = await go2rtc_mgr.get_streams_status()

    result = []
    for sid, stream in streams.items():
        result.append({
            "id": sid,
            "name": stream.name,
            "url": stream.url,
            "active": sid in go2rtc_status,
        })
    return result


@router.post("/streams", status_code=201)
async def add_stream(body: StreamCreate, request: Request):
    config_mgr = request.app.state.config_mgr
    go2rtc_mgr = request.app.state.go2rtc_mgr

    stream_id = config_mgr.add_stream(None, body.name, body.url)
    await go2rtc_mgr.add_stream(stream_id, body.url)

    return {"id": stream_id, "name": body.name, "url": body.url}


@router.put("/streams/{stream_id}")
async def update_stream(stream_id: str, body: StreamUpdate, request: Request):
    config_mgr = request.app.state.config_mgr
    go2rtc_mgr = request.app.state.go2rtc_mgr

    try:
        old_stream = config_mgr.get_streams().get(stream_id)
        if not old_stream:
            raise KeyError(stream_id)

        config_mgr.update_stream(stream_id, name=body.name, url=body.url)

        # If URL changed, update go2rtc
        if body.url and body.url != old_stream.url:
            await go2rtc_mgr.remove_stream(stream_id)
            await go2rtc_mgr.add_stream(stream_id, body.url)

        updated = config_mgr.get_streams()[stream_id]
        return {"id": stream_id, "name": updated.name, "url": updated.url}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Stream '{stream_id}' not found")


@router.delete("/streams/{stream_id}", status_code=204)
async def delete_stream(stream_id: str, request: Request):
    config_mgr = request.app.state.config_mgr
    go2rtc_mgr = request.app.state.go2rtc_mgr

    try:
        config_mgr.remove_stream(stream_id)
        await go2rtc_mgr.remove_stream(stream_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Stream '{stream_id}' not found")
