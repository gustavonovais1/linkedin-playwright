from fastapi import APIRouter, Query
from services.instagram import media_list, get_profile, get_insights_profile, get_insights_posts, exchange_token_service
from fastapi import Depends
from core.auth import get_current_user_oauth
from models.models_user import User

router = APIRouter()

@router.get("/profile")
def ig_profile(fields: str = Query("id,username,name,profile_picture_url,biography,followers_count,follows_count,media_count,website"), user: User = Depends(get_current_user_oauth)):
    """
    Perfil do Instagram (Graph API).
    Parâmetros:
    - fields: Campos a retornar (id, username, name, biography, etc.).
    Retorna:
    - Metadados do perfil e contagens.
    """
    return get_profile(fields=fields)

@router.get("/media")
def ig_media(fields: str = Query("id,media_type,timestamp"), limit: int = Query(25, ge=1, le=100), media_type: str | None = None, since: int | str | None = None, until: int | str | None = None, user: User = Depends(get_current_user_oauth)):
    """
    Lista mídias do Instagram (Graph API).
    Parâmetros:
    - fields: Campos a retornar (ex.: id, media_type, timestamp, caption, media_url).
    - limit: Quantidade por página (1–100).
    - media_type: Filtro por tipos (ex.: IMAGE, VIDEO, CAROUSEL_ALBUM).
    - since/until: Intervalo temporal (timestamp UNIX ou YYYY-MM-DD).
    Retorna:
    - Estrutura original da Graph API com `data` filtrada conforme parâmetros.
    """
    return media_list(fields=fields, limit=limit, media_type=media_type, since=since, until=until)

@router.get("/insights/profile")
def ig_insights_profile(metric: str = "reach, website_clicks, profile_views, accounts_engaged, total_interactions, likes, comments, shares, saves, replies, follows_and_unfollows, profile_links_taps, views, reposts, content_views", since: int | str | None = None, until: int | str | None = None, user: User = Depends(get_current_user_oauth)):
    """
    Insights agregados do perfil.
    Parâmetros:
    - metric: lista de métricas suportadas.
    - since/until: intervalo temporal (timestamp ou ISO).
    """
    return get_insights_profile(metric=metric, since=since, until=until)

@router.get("/insights/posts")
def ig_insights_posts(media_id: str = Query(...), metric: str = Query("views,reach,saved,likes,comments,shares,total_interactions,reposts"), user: User = Depends(get_current_user_oauth)):
    """
    Insights por post (Instagram Graph API).
    Parâmetros:
    - media_id: ID da mídia alvo.
    - metric: Lista de métricas suportadas.
    Suporte por tipo:
    - IMAGE/CAROUSEL_ALBUM: views, reach, saved, likes, comments, shares, total_interactions, follows, profile_visits, profile_activity, reposts
    - VIDEO/REELS: views, reach, saved, likes, comments, shares, total_interactions, ig_reels_video_view_total_time, ig_reels_avg_watch_time, reels_skip_rate, reposts, facebook_views, crossposted_views
    Retorna:
    - JSON com `data` das métricas e persiste os valores agregados no banco.
    """
    return get_insights_posts(media_id=media_id, metric=metric)

@router.get("/oauth/exchange_token")
def oauth_exchange_token(fb_exchange_token: str = Query(...), user: User = Depends(get_current_user_oauth)):
    """
    Troca de token curto por token de longo prazo (Meta OAuth).
    Parâmetros:
    - fb_exchange_token: token curto da API do Facebook.
    Retorna:
    - access_token e expires_in; persiste em banco.
    """
    return exchange_token_service(fb_exchange_token=fb_exchange_token)
