"""WebRTC signaling proxy to go2rtc."""

from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter(tags=["webrtc"])


@router.post("/webrtc")
async def webrtc_offer(src: str, request: Request):
    go2rtc_mgr = request.app.state.go2rtc_mgr

    body = await request.body()
    content_type = request.headers.get("content-type", "application/sdp")

    try:
        resp = await go2rtc_mgr.webrtc_offer(src, body, content_type)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"go2rtc error: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return Response(
        content=resp.content,
        media_type=resp.headers.get("content-type", "application/sdp"),
    )
