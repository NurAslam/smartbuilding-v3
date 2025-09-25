from fastapi import APIRouter, Query
from ..schemas import SurfaceComfortResponse
from ..domain.surface import resolve_ceiling, surface_ac, surface_non_ac, TABLE_NON_AC
from ..domain.comfort import comfort_index, index_label

router = APIRouter(tags=["simulation-info"])

SIM_APP_VERSION = "1.2.0"


@router.get("/status")
def health():
    return {"status": "ok", "version": SIM_APP_VERSION}


@router.get("/list-ceiling")
def list_ceiling():
    return {"ceiling": list(TABLE_NON_AC.keys())}


@router.get("/surface-comfort", response_model=SurfaceComfortResponse)
def surface_and_comfort(
    T_out: float = Query(..., description="Outdoor temperature (°C)"),
    T_in: float  = Query(..., description="Indoor temperature (°C)"),
    humidity: float = Query(50, ge=0, le=100, description="Kelembapan relatif (%)"),
    wind_speed: float = Query(0, ge=0, description="Kecepatan angin (m/s)"),
    ceiling: str = Query(..., description="Nama Konstruksi"),
):
    name = resolve_ceiling(ceiling)
    s_non = surface_non_ac(T_out, name)
    s_ac  = surface_ac(T_in, name)
    idx   = comfort_index(T_in, humidity, wind_speed)
    return SurfaceComfortResponse(
        ceiling=name,
        T_out=T_out,
        T_in=T_in,
        surface_non_ac=s_non,
        surface_ac=s_ac,
        index=idx,
        label=index_label(idx),
    )
