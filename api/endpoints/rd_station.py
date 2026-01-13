from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import RedirectResponse, HTMLResponse
import os
from datetime import datetime, timedelta

from core.auth import get_current_user_oauth
from models.models_user import User
from services.rd_station import (
    get_conversions_analytics,
    get_email_analytics,
    get_segmentations,
    get_landing_pages,
    get_workflows,
    oauth_callback,
)

router = APIRouter()


@router.get("/auth")
def rd_auth_redirect():
    """
    Inicia o fluxo OAuth do RD Station Marketing.
    Redireciona o navegador para a tela de autorização do RD Station.
    Retorna:
    - Redirect para a URL de autenticação com client_id e redirect_uri.
    """
    client_id = os.environ.get("RD_ACCOUNT_ID")
    redirect_uri = os.environ.get("URL_CALLBACK")
    auth_url = f"https://app.rdstation.com.br/api/platform/auth?client_id={client_id}&redirect_uri={redirect_uri}"
    return RedirectResponse(auth_url)


@router.get("/oauth/callback", include_in_schema=False)
def rd_oauth_callback(code: str = Query(...)):
    """
    Callback OAuth do RD Station.
    Parâmetros:
    - code: Código de autorização recebido do RD.
    Ação:
    - Troca o code por access_token e salva no banco.
    Retorna:
    - HTML de sucesso para fechar a janela.
    """
    redirect_uri = os.environ.get("URL_CALLBACK")
    oauth_callback(code=code, redirect_uri=redirect_uri)
    return HTMLResponse(content="""
        <html>
            <body style="font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background-color: #f4f7f6;">
                <div style="text-align: center; padding: 40px; background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h1 style="color: #2e7d32;">Autenticação Concluída!</h1>
                    <p>O token do RD Station foi salvo com sucesso.</p>
                    <p style="color: #666;">Você já pode fechar esta janela e usar a API.</p>
                    <button onclick="window.close()" style="margin-top: 20px; padding: 10px 20px; background-color: #2196f3; color: white; border: none; border-radius: 4px; cursor: pointer;">Fechar Janela</button>
                </div>
            </body>
        </html>
    """)


@router.get("/analytics/emails")
def rd_analytics_emails(
    start_date: str = Query(
        default=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        description="Data de início (yyyy-mm-dd)",
    ),
    end_date: str = Query(
        default=datetime.now().strftime("%Y-%m-%d"),
        description="Data de fim (yyyy-mm-dd)",
    ),
    user: User = Depends(get_current_user_oauth),
):
    """
    Métricas de desempenho de campanhas de email no RD Station.
    Parâmetros:
    - start_date, end_date: janela de análise (padrão últimos 30 dias).
    Retorna:
    - Estatísticas agregadas e persiste no banco.
    """
    return get_email_analytics(start_date, end_date)


@router.get("/analytics/conversions")
def rd_analytics_conversions(
    start_date: str = Query(
        default=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        description="Data de início (yyyy-mm-dd)",
    ),
    end_date: str = Query(
        default=datetime.now().strftime("%Y-%m-%d"),
        description="Data de fim (yyyy-mm-dd)",
    ),
    user: User = Depends(get_current_user_oauth),
):
    """
    Métricas de conversões (funil) no RD Station.
    Parâmetros:
    - start_date, end_date: janela de análise (padrão últimos 30 dias).
    Retorna:
    - Estatísticas de conversões e persiste no banco.
    """
    return get_conversions_analytics(start_date, end_date)


@router.get("/segmentations")
def rd_segmentations(user: User = Depends(get_current_user_oauth)):
    """
    Lista segmentações configuradas no RD Station.
    Retorna:
    - Array de segmentações e persiste no banco.
    """
    return get_segmentations()


@router.get("/landing_pages")
def rd_landing_pages(user: User = Depends(get_current_user_oauth)):
    """
    Lista landing pages cadastradas no RD Station.
    Retorna:
    - Array de páginas e persiste no banco.
    """
    return get_landing_pages()


@router.get("/workflows")
def rd_workflows(user: User = Depends(get_current_user_oauth)):
    """
    Lista workflows ativos/definidos no RD Station.
    Retorna:
    - Array de workflows e persiste no banco.
    """
    return get_workflows()
