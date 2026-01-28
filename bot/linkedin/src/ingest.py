import os
import re
import datetime
import calendar
import pandas as pd
from core.db import Base, engine, get_session
from models.models_linkedin import Competitor, Follower, Update as UpdateModel, Visitor

def _get_env(name, default=None):
    v = os.environ.get(name)
    return v if v is not None else default

def _session():
    return get_session()

def _month_period_string(dt):
    name = calendar.month_name[dt.month].lower()
    return f"{name}/{dt.year}"

def _read_excel_raw(path):
    ext = os.path.splitext(path)[1].lower()
    engine = "openpyxl" if ext == ".xlsx" else "xlrd"
    return pd.read_excel(path, engine=engine, header=None)

def _find_header_row(df: pd.DataFrame, kind: str | None) -> int | None:
    try:
        max_scan = min(len(df), 50)
        for i in range(max_scan):
            row = [str(x).strip() for x in list(df.iloc[i].values)]
            if kind == "competitors":
                if any(x.lower() == "page" for x in row):
                    return i
            else:
                if any(x.lower() in ("data", "date") for x in row):
                    return i
        return None
    except Exception:
        return None

def _read_excel_structured(path, kind):
    dfr = _read_excel_raw(path)
    hdr = _find_header_row(dfr, kind)
    if hdr is None:
        return dfr
    header = [str(x).strip() for x in list(dfr.iloc[hdr].values)]
    df = dfr.iloc[hdr + 1:].copy()
    df.columns = header
    # drop fully empty rows
    try:
        df = df.dropna(how="all")
    except Exception:
        pass
    return df

def _to_int(s):
    try:
        return int(s) if pd.notna(s) else 0
    except Exception:
        try:
            return int(float(str(s).replace("%", "").replace(",", ".")))
        except Exception:
            return 0

def _to_rate(s):
    if pd.isna(s):
        return 0.0
    try:
        if isinstance(s, str) and "%" in s:
            v = float(s.replace("%", "").replace(",", ".")) / 100.0
            return v
        return float(s)
    except Exception:
        try:
            return float(str(s).replace(",", "."))
        except Exception:
            return 0.0

def _detect_dayfirst(series: pd.Series) -> bool:
    """
    Detects if the date format is DMY (dayfirst=True) or MDY (dayfirst=False).
    Returns True for DMY, False for MDY.
    """
    dmy_score = 0
    mdy_score = 0
    
    for val in series:
        if pd.isna(val):
            continue
        s = str(val).strip()
        # Match XX/XX/XXXX or XX-XX-XXXX
        m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?:\s+.*)?$", s)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a > 12:
                dmy_score += 1 # A must be day -> DMY
            if b > 12:
                mdy_score += 1 # B must be day -> MDY

    # Prioritize detected format
    if dmy_score > 0 and mdy_score == 0:
        return True
    if mdy_score > 0 and dmy_score == 0:
        return False
        
    # Default to MDY (False) if ambiguous or mixed, as per user context (LinkedIn US export usually MDY)
    return False

def _to_date(s, dayfirst=False):
    if pd.isna(s):
        return None
    if isinstance(s, datetime.date) and not isinstance(s, datetime.datetime):
        return s
    if isinstance(s, datetime.datetime):
        return s.date()
    
    s_str = str(s).strip()
    
    # ISO format YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s_str):
        try:
            return datetime.date.fromisoformat(s_str)
        except Exception:
            return None

    # Common formats XX/XX/XXXX
    if re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{4}(?:\s+.*)?$", s_str):
        try:
            dt = pd.to_datetime(s_str, dayfirst=dayfirst)
            return dt.date()
        except Exception:
            return None
            
    # Try numeric (Excel serial)
    try:
        # Check if strictly numeric to avoid loose parsing of strings like "Jan 2026"
        float(s_str)
        dt = pd.to_datetime(s)
        return dt.date()
    except Exception:
        pass

    return None

def _parse_period_from_filename(fn: str) -> str:
    m = re.search(r"_(\d{2})-(\d{2})-(\d{4})_(\d{2})-(\d{2})-(\d{4})", fn)
    if m:
        try:
            end = datetime.date(int(m.group(6)), int(m.group(5)), int(m.group(4)))
            return _month_period_string(end)
        except Exception:
            pass
    now = datetime.datetime.utcnow()
    return _month_period_string(now)

def _extract_range_from_filename(fn: str):
    m = re.search(r"_(\d{2})-(\d{2})-(\d{4})_(\d{2})-(\d{2})-(\d{4})", fn)
    if not m:
        return None, None
    try:
        start = datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        end = datetime.date(int(m.group(6)), int(m.group(5)), int(m.group(4)))
        return start, end
    except Exception:
        return None, None

def _process_competitors(df, s, source_name: str):
    period = _parse_period_from_filename(source_name)
    mapping = {
        "Page": "page",
        "Total de seguidores": "total_followers",
        "Novos seguidores": "new_followers",
        "Total de engajamentos da publicação": "total_post_engagements",
        "Total de publicações": "total_posts",
    }
    cols = {k: v for k, v in mapping.items() if k in df.columns}
    dfo = df.rename(columns=cols)
    dfo["total_followers"] = dfo.get("total_followers", pd.Series(dtype="float")).apply(_to_int)
    dfo["new_followers"] = dfo.get("new_followers", pd.Series(dtype="float")).apply(_to_int)
    dfo["total_post_engagements"] = dfo.get("total_post_engagements", pd.Series(dtype="float")).apply(_to_int)
    dfo["total_posts"] = dfo.get("total_posts", pd.Series(dtype="float")).apply(_to_int)
    cnt = 0
    for _, row in dfo.iterrows():
        key = (period, row.get("page"))
        obj = s.get(Competitor, key)
        if obj is None:
            obj = Competitor(period=period, page=row.get("page"))
            try:
                obj.created_at = datetime.datetime.utcnow()
            except Exception:
                pass
        obj.total_followers = row.get("total_followers")
        obj.new_followers = row.get("new_followers")
        obj.total_post_engagements = row.get("total_post_engagements")
        obj.total_posts = row.get("total_posts")
        try:
            obj.updated_at = datetime.datetime.utcnow()
        except Exception:
            pass
        s.add(obj)
        cnt += 1
    s.commit()
    return cnt

def _process_followers(df, s, source_name: str = ""):
    mapping = {
        "Data": "date",
        "Date": "date",
        "Seguidores patrocinados": "sponsored_followers",
        "Seguidores orgânicos": "organic_followers",
        "Seguidores convidados automaticamente": "auto_invited_followers",
        "Total de seguidores": "total_followers",
    }
    cols = {k: v for k, v in mapping.items() if k in df.columns}
    dfo = df.rename(columns=cols)
    raw_dates = dfo.get("date", pd.Series(dtype="object"))
    is_dayfirst = _detect_dayfirst(raw_dates)
    dfo["date"] = raw_dates.apply(lambda x: _to_date(x, dayfirst=is_dayfirst))
    # filtra datas válidas e dentro do intervalo do arquivo, se disponível
    try:
        dfo = dfo.dropna(subset=["date"])
    except Exception:
        pass
    start, end = _extract_range_from_filename(source_name or "")
    if start and end:
        try:
            dfo = dfo[(dfo["date"] >= start) & (dfo["date"] <= end)]
        except Exception:
            pass
    dfo["sponsored_followers"] = dfo.get("sponsored_followers", pd.Series(dtype="float")).apply(_to_int)
    dfo["organic_followers"] = dfo.get("organic_followers", pd.Series(dtype="float")).apply(_to_int)
    dfo["auto_invited_followers"] = dfo.get("auto_invited_followers", pd.Series(dtype="float")).apply(_to_int)
    dfo["total_followers"] = dfo.get("total_followers", pd.Series(dtype="float")).apply(_to_int)
    cnt = 0
    for _, row in dfo.iterrows():
        if not row.get("date"):
            continue
        obj = s.get(Follower, row.get("date"))
        if obj is None:
            obj = Follower(date=row.get("date"))
            try:
                obj.created_at = datetime.datetime.utcnow()
            except Exception:
                pass
        obj.sponsored_followers = row.get("sponsored_followers")
        obj.organic_followers = row.get("organic_followers")
        obj.auto_invited_followers = row.get("auto_invited_followers")
        obj.total_followers = row.get("total_followers")
        try:
            obj.updated_at = datetime.datetime.utcnow()
        except Exception:
            pass
        s.add(obj)
        cnt += 1
    s.commit()
    return cnt

def _process_updates(df, s, source_name: str = ""):
    mapping = {
        "Data": "date",
        "Date": "date",
        "Impressões (orgânicas)": "impressions_organic",
        "Impressões (patrocinadas)": "impressions_sponsored",
        "Impressões (total)": "impressions_total",
        "Impressões únicas (orgânicas)": "unique_impressions_organic",
        "Cliques (orgânicos)": "clicks_organic",
        "Cliques (patrocinados)": "clicks_sponsored",
        "Cliques (total)": "clicks_total",
        "Reações (orgânicas)": "reactions_organic",
        "Reações (patrocinadas)": "reactions_sponsored",
        "Reações (total)": "reactions_total",
        "Comentários (orgânicos)": "comments_organic",
        "Comentários (patrocinados)": "comments_sponsored",
        "Comentários (total)": "comments_total",
        "Compartilhamentos (orgânicos)": "shares_organic",
        "Compartilhamentos (patrocinados)": "shares_sponsored",
        "Compartilhamentos (total)": "shares_total",
        "Taxa de engajamento (orgânico)": "engagement_rate_organic",
        "Taxa de engajamento (patrocinado)": "engagement_rate_sponsored",
        "Taxa de engajamento (total)": "engagement_rate_total",
    }
    cols = {k: v for k, v in mapping.items() if k in df.columns}
    dfo = df.rename(columns=cols)
    raw_dates = dfo.get("date", pd.Series(dtype="object"))
    is_dayfirst = _detect_dayfirst(raw_dates)
    dfo["date"] = raw_dates.apply(lambda x: _to_date(x, dayfirst=is_dayfirst))
    try:
        dfo = dfo.dropna(subset=["date"])
    except Exception:
        pass
    start, end = _extract_range_from_filename(source_name or "")
    if start and end:
        try:
            dfo = dfo[(dfo["date"] >= start) & (dfo["date"] <= end)]
        except Exception:
            pass
    for k in [
        "impressions_organic",
        "impressions_sponsored",
        "impressions_total",
        "unique_impressions_organic",
        "clicks_organic",
        "clicks_sponsored",
        "clicks_total",
        "reactions_organic",
        "reactions_sponsored",
        "reactions_total",
        "comments_organic",
        "comments_sponsored",
        "comments_total",
        "shares_organic",
        "shares_sponsored",
        "shares_total",
    ]:
        dfo[k] = dfo.get(k, pd.Series(dtype="float")).apply(_to_int)
    for k in [
        "engagement_rate_organic",
        "engagement_rate_sponsored",
        "engagement_rate_total",
    ]:
        dfo[k] = dfo.get(k, pd.Series(dtype="float")).apply(_to_rate)
    cnt = 0
    for _, row in dfo.iterrows():
        if not row.get("date"):
            continue
        obj = s.get(UpdateModel, row.get("date"))
        if obj is None:
            obj = UpdateModel(date=row.get("date"))
            try:
                obj.created_at = datetime.datetime.utcnow()
            except Exception:
                pass
        for k in [
            "impressions_organic",
            "impressions_sponsored",
            "impressions_total",
            "unique_impressions_organic",
            "clicks_organic",
            "clicks_sponsored",
            "clicks_total",
            "reactions_organic",
            "reactions_sponsored",
            "reactions_total",
            "comments_organic",
            "comments_sponsored",
            "comments_total",
            "shares_organic",
            "shares_sponsored",
            "shares_total",
            "engagement_rate_organic",
            "engagement_rate_sponsored",
            "engagement_rate_total",
        ]:
            setattr(obj, k, row.get(k))
        try:
            obj.updated_at = datetime.datetime.utcnow()
        except Exception:
            pass
        s.add(obj)
        cnt += 1
    s.commit()
    return cnt

def _process_visitors(df, s, source_name: str = ""):
    mapping = {
        "Data": "date",
        "Date": "date",
        "Visualizações da página Visão geral (computadores)": "overview_page_views_desktop",
        "Visualizações da página Visão geral (dispositivos móveis)": "overview_page_views_mobile",
        "Visualizações da página Visão geral (total)": "overview_page_views_total",
        "Visitantes únicos da página Visão geral (computadores)": "overview_unique_visitors_desktop",
        "Visitantes únicos da página Visão geral (dispositivos móveis)": "overview_unique_visitors_mobile",
        "Visitantes únicos da página Visão geral (total)": "overview_unique_visitors_total",
        "Visualizações da página Dia a dia (computadores)": "day_by_day_page_views_desktop",
        "Visualizações da página Dia a dia (dispositivos móveis)": "day_by_day_page_views_mobile",
        "Visualizações da página Dia a dia (total)": "day_by_day_page_views_total",
        "Visitantes únicos da página Dia a dia (computadores)": "day_by_day_unique_visitors_desktop",
        "Visitantes únicos da página Dia a dia (dispositivos móveis)": "day_by_day_unique_visitors_mobile",
        "Visitantes únicos da página Dia a dia (total)": "day_by_day_unique_visitors_total",
        "Visualizações da página Vagas (computadores)": "jobs_page_views_desktop",
        "Visualizações da página Vagas (dispositivos móveis)": "jobs_page_views_mobile",
        "Visualizações da página Vagas (total)": "jobs_page_views_total",
        "Visitantes únicos da página Vagas (computadores)": "jobs_unique_visitors_desktop",
        "Visitantes únicos da página Vagas (dispositivos móveis)": "jobs_unique_visitors_mobile",
        "Visitantes únicos da página Vagas (total)": "jobs_unique_visitors_total",
        "Total de visualizações da página (computadores)": "total_page_views_desktop",
        "Total de visualizações da página (dispositivos móveis)": "total_page_views_mobile",
        "Total de visualizações da página (total)": "total_page_views_total",
        "Total de visitantes únicos (computadores)": "total_unique_visitors_desktop",
        "Total de visitantes únicos (dispositivos móveis)": "total_unique_visitors_mobile",
        "Total de visitantes únicos (total)": "total_unique_visitors_total",
    }
    cols = {k: v for k, v in mapping.items() if k in df.columns}
    dfo = df.rename(columns=cols)
    raw_dates = dfo.get("date", pd.Series(dtype="object"))
    is_dayfirst = _detect_dayfirst(raw_dates)
    dfo["date"] = raw_dates.apply(lambda x: _to_date(x, dayfirst=is_dayfirst))
    try:
        dfo = dfo.dropna(subset=["date"])
    except Exception:
        pass
    start, end = _extract_range_from_filename(source_name or "")
    if start and end:
        try:
            dfo = dfo[(dfo["date"] >= start) & (dfo["date"] <= end)]
        except Exception:
            pass
    for k in [
        "overview_page_views_desktop",
        "overview_page_views_mobile",
        "overview_page_views_total",
        "overview_unique_visitors_desktop",
        "overview_unique_visitors_mobile",
        "overview_unique_visitors_total",
        "day_by_day_page_views_desktop",
        "day_by_day_page_views_mobile",
        "day_by_day_page_views_total",
        "day_by_day_unique_visitors_desktop",
        "day_by_day_unique_visitors_mobile",
        "day_by_day_unique_visitors_total",
        "jobs_page_views_desktop",
        "jobs_page_views_mobile",
        "jobs_page_views_total",
        "jobs_unique_visitors_desktop",
        "jobs_unique_visitors_mobile",
        "jobs_unique_visitors_total",
        "total_page_views_desktop",
        "total_page_views_mobile",
        "total_page_views_total",
        "total_unique_visitors_desktop",
        "total_unique_visitors_mobile",
        "total_unique_visitors_total",
    ]:
        dfo[k] = dfo.get(k, pd.Series(dtype="float")).apply(_to_int)
    cnt = 0
    for _, row in dfo.iterrows():
        if not row.get("date"):
            continue
        obj = s.get(Visitor, row.get("date"))
        if obj is None:
            obj = Visitor(date=row.get("date"))
            try:
                obj.created_at = datetime.datetime.utcnow()
            except Exception:
                pass
        for k in [
            "overview_page_views_desktop",
            "overview_page_views_mobile",
            "overview_page_views_total",
            "overview_unique_visitors_desktop",
            "overview_unique_visitors_mobile",
            "overview_unique_visitors_total",
            "day_by_day_page_views_desktop",
            "day_by_day_page_views_mobile",
            "day_by_day_page_views_total",
            "day_by_day_unique_visitors_desktop",
            "day_by_day_unique_visitors_mobile",
            "day_by_day_unique_visitors_total",
            "jobs_page_views_desktop",
            "jobs_page_views_mobile",
            "jobs_page_views_total",
            "jobs_unique_visitors_desktop",
            "jobs_unique_visitors_mobile",
            "jobs_unique_visitors_total",
            "total_page_views_desktop",
            "total_page_views_mobile",
            "total_page_views_total",
            "total_unique_visitors_desktop",
            "total_unique_visitors_mobile",
            "total_unique_visitors_total",
        ]:
            setattr(obj, k, row.get(k))
        try:
            obj.updated_at = datetime.datetime.utcnow()
        except Exception:
            pass
        s.add(obj)
        cnt += 1
    s.commit()
    return cnt

def ingest_downloads(downloads_dir):
    s = _session()
    # _ensure_orm_tables() removido - core/db.py ja faz isso
    files = []
    try:
        for name in os.listdir(downloads_dir):
            if name.lower().endswith((".xls", ".xlsx")):
                files.append(os.path.join(downloads_dir, name))
    except Exception:
        files = []
    for path in files:
        fn = os.path.basename(path)
        m = re.match(r"linkedin_(\w+)_", fn)
        kind = m.group(1) if m else ""
        processed = 0
        try:
            df = _read_excel_structured(path, kind)
        except Exception:
            df = None
        if df is None or df.empty:
            try:
                os.remove(path)
            except Exception:
                pass
            continue
        try:
            if kind == "competitors":
                processed = _process_competitors(df, s, fn)
            elif kind == "followers":
                processed = _process_followers(df, s, fn)
            elif kind == "updates":
                processed = _process_updates(df, s, fn)
            elif kind == "visitors":
                processed = _process_visitors(df, s, fn)
        except Exception:
            processed = 0
        if processed > 0:
            try:
                os.remove(path)
            except Exception:
                pass
    try:
        s.close()
    except Exception:
        pass

if __name__ == "__main__":
    dd = _get_env("DOWNLOADS_DIR", "/app/linkedin/downloads")
    ingest_downloads(dd)
