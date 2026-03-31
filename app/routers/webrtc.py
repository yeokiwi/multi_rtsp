"""WebRTC signaling proxy to go2rtc."""

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

logger = logging.getLogger("webrtc_proxy")

router = APIRouter(tags=["webrtc"])


@router.post("/webrtc")
async def webrtc_offer(src: str, request: Request):
    go2rtc_mgr = request.app.state.go2rtc_mgr

    if not go2rtc_mgr.is_running():
        raise HTTPException(status_code=503, detail="go2rtc is restarting, please retry")

    try:
        raw_body = await request.body()
        sdp_offer = raw_body.decode("utf-8", errors="replace")

        resp = await go2rtc_mgr.webrtc_offer(src, sdp_offer)

        if resp.status_code != 200:
            detail = resp.text
            logger.error("go2rtc returned %d for stream '%s': %s", resp.status_code, src, detail)
            raise HTTPException(status_code=resp.status_code, detail=detail)

        # Pass go2rtc's response through faithfully
        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "application/sdp"),
        )

    except HTTPException:
        raise
    except (httpx.ReadError, httpx.ConnectError, httpx.RemoteProtocolError):
        # go2rtc is likely restarting — tell client to retry
        logger.warning("go2rtc unavailable for stream '%s' (likely restarting)", src)
        raise HTTPException(status_code=503, detail="go2rtc is restarting, please retry")
    except Exception as e:
        logger.exception("WebRTC signaling failed for stream '%s'", src)
        raise HTTPException(status_code=502, detail=f"go2rtc signaling error: {e}")
