from fastapi import APIRouter, Depends, Query
from typing import Optional
from services.viva_engage import (
    list_communities, 
    get_community_details, 
    get_ve_token, 
    report_yammer_groups_activity_counts,
    report_yammer_groups_activity_detail,
    report_yammer_activity_user_detail,
    report_yammer_device_usage_user_detail,
    report_yammer_activity_user_counts
)
from core.auth import get_current_user_oauth
from models.models_user import User

router = APIRouter()

@router.get("/token")
def ve_get_token(user: User = Depends(get_current_user_oauth)):
    """
    Retorna o token de acesso atual (ou gera um novo).
    """
    return {"access_token": get_ve_token()}

@router.get("/communities")
def ve_list_communities(
    select: Optional[str] = Query(None, description="Propriedades para retornar"),
    top: Optional[int] = Query(None, description="Limite de registros"),
    user: User = Depends(get_current_user_oauth)
):
    """
    Lista comunidades do Viva Engage via Microsoft Graph.
    Parâmetros:
    - select: Propriedades a retornar (ex.: displayName,groupId).
    - top: Limite de registros por página.
    Retorna:
    - JSON com metadados de comunidades (id, displayName, groupId, privacy).
    """
    return list_communities(select=select, top=top)

@router.get("/communities/{community_id}")
def ve_community_details(community_id: str, user: User = Depends(get_current_user_oauth)):
    """
    Detalhes de uma comunidade específica do Viva Engage.
    Parâmetros:
    - community_id: ID único da comunidade.
    Retorna:
    - Metadados da comunidade (displayName, groupId, privacy, etc.).
    """
    return get_community_details(community_id)

@router.get("/reports/yammer/groups/activity-counts")
def ve_reports_yammer_groups_activity_counts(
    period: str = Query("D30", description="Período: D7, D30, D90, D180"),
    user: User = Depends(get_current_user_oauth)
):
    """
    Métricas de atividade da rede (contagens por dia).
    Fonte: Microsoft 365 usage reports (Yammer).
    Parâmetros:
    - period: Janela de tempo (D7, D30, D90, D180).
    Retorna:
    - Série temporal CSV convertida para JSON (Liked, Posted, Read, Report Date).
    """
    return report_yammer_groups_activity_counts(period)

@router.get("/reports/yammer/groups/activity-detail")
def ve_reports_yammer_groups_activity_detail(
    period: str = Query("D30", description="Período: D7, D30, D90, D180"),
    user: User = Depends(get_current_user_oauth)
):
    """
    Performance por comunidade (ranking de engajamento).
    Fonte: Microsoft 365 usage reports (Yammer).
    Parâmetros:
    - period: Janela de tempo (D7, D30, D90, D180).
    Retorna:
    - Detalhe por grupo (Group Display Name, Member Count, Posted/Read/Liked Count).
    """
    return report_yammer_groups_activity_detail(period)

@router.get("/reports/yammer/users/activity-detail")
def ve_reports_yammer_activity_user_detail(
    period: str = Query("D30", description="Período: D7, D30, D90, D180"),
    user: User = Depends(get_current_user_oauth)
):
    """
    Detalhes de atividade por usuário (influenciadores).
    Fonte: Microsoft 365 usage reports (Yammer).
    Parâmetros:
    - period: Janela de tempo (D7, D30, D90, D180).
    Retorna:
    - User Principal Name, Last Activity Date, Posted/Read/Liked (contagens).
    """
    return report_yammer_activity_user_detail(period)

@router.get("/reports/yammer/devices/usage-detail")
def ve_reports_yammer_device_usage_user_detail(
    period: str = Query("D30", description="Período: D7, D30, D90, D180"),
    user: User = Depends(get_current_user_oauth)
):
    """
    Uso de dispositivos/plataformas de acesso.
    Fonte: Microsoft 365 usage reports (Yammer).
    Parâmetros:
    - period: Janela de tempo (D7, D30, D90, D180).
    Retorna:
    - Colunas booleanas: Web, Android, iPhone, iPad por usuário.
    """
    return report_yammer_device_usage_user_detail(period)

@router.get("/reports/yammer/users/activity-counts")
def ve_reports_yammer_activity_user_counts(
    period: str = Query("D30", description="Período: D7, D30, D90, D180"),
    user: User = Depends(get_current_user_oauth)
):
    """
    Alcance de usuários únicos (DAU/MAU por ação).
    Fonte: Microsoft 365 usage reports (Yammer).
    Parâmetros:
    - period: Janela de tempo (D7, D30, D90, D180).
    Retorna:
    - Contagem de indivíduos únicos para Liked, Posted, Read por dia.
    """
    return report_yammer_activity_user_counts(period)
