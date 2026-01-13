import os
import requests
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from core.db import get_session
from models.models_viva_engage import VEToken, VECommunity, VEReportGroupsActivityCounts, VEReportGroupsActivityDetail, VEReportUserActivityDetail, VEReportDeviceUsageUserDetail, VEReportUserActivityCounts

TENANT_ID = os.getenv("VE_DIRECTORY_TENANT_ID")
CLIENT_ID = os.getenv("VE_APPLICATION_CLIENT_ID")
CLIENT_SECRET = os.getenv("VE_SECRET")

def get_ve_token():
    """
    Obtém um token de acesso para o Microsoft Graph usando Client Credentials Flow.
    """
    s = get_session()
    try:
        token_obj = s.query(VEToken).filter(VEToken.id == "current").first()
        
        if token_obj and token_obj.expires_at > datetime.now(timezone.utc):
            return token_obj.access_token

        # Se não houver token ou estiver expirado, solicita um novo
        url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default"
        }
        
        response = requests.post(url, data=data, timeout=30)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Erro ao obter token do Viva Engage: {response.text}")
        
        token_data = response.json()
        access_token = token_data["access_token"]
        expires_in = token_data["expires_in"]
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        if not token_obj:
            token_obj = VEToken(id="current")
        
        token_obj.access_token = access_token
        token_obj.expires_at = expires_at
        s.add(token_obj)
        s.commit()
        
        return access_token
    finally:
        s.close()

def _ve_get(path: str, version: str = "v1.0", params: dict = None):
    token = get_ve_token()
    url = f"https://graph.microsoft.com/{version}/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=60)
    if response.status_code >= 400:
        try:
            detail = response.json()
        except:
            detail = {"error": response.text, "status": response.status_code}
        raise HTTPException(status_code=response.status_code, detail=detail)
    
    return response.json()

def _persist_communities(communities_list):
    """
    Persiste a lista de comunidades no banco de dados.
    """
    s = get_session()
    try:
        for item in communities_list:
            comm_id = item.get("id")
            if not comm_id: continue
            
            obj = s.query(VECommunity).filter(VECommunity.id == comm_id).first()
            if not obj:
                obj = VECommunity(id=comm_id)
            
            obj.group_id = item.get("groupId")
            obj.display_name = item.get("displayName")
            obj.description = item.get("description")
            obj.privacy = item.get("privacy")
            
            created_str = item.get("createdDateTime")
            if created_str:
                try:
                    obj.created_at_ve = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                except:
                    pass
            s.add(obj)
        s.commit()
    except Exception as e:
        print(f"Erro ao persistir comunidades do Viva Engage: {e}")
        s.rollback()
    finally:
        s.close()

def test_token():
    raise HTTPException(status_code=404, detail={"error": "endpoint removido"})

def list_communities(select: str = None, top: int = None):
    params = {}
    if select:
        params["$select"] = select
    if top is not None:
        params["$top"] = int(top)
    data = _ve_get("employeeExperience/communities", version="v1.0", params=params or None)
    communities = data.get("value", [])
    _persist_communities(communities)
    return data

def get_community_details(community_id: str):
    """
    Obtém detalhes de uma comunidade específica.
    Requer: Community.Read.All
    """
    return _ve_get(f"employeeExperience/communities/{community_id}", version="v1.0")

def get_engagement_analytics(start_date: str = None, end_date: str = None):
    raise HTTPException(status_code=404, detail={"error": "endpoint removido"})

def get_community_analytics(community_id: str):
    raise HTTPException(status_code=404, detail={"error": "endpoint removido"})

def list_conversations(community_id: str = None):
    raise HTTPException(status_code=404, detail={"error": "endpoint removido"})

def _ve_get_csv(path: str, version: str = "v1.0"):
    token = get_ve_token()
    url = f"https://graph.microsoft.com/{version}/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/csv"
    }
    response = requests.get(url, headers=headers, timeout=60)
    if response.status_code >= 400:
        try:
            detail = response.json()
        except:
            detail = {"error": response.text, "status": response.status_code}
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.text

def _parse_csv(text_csv: str):
    import csv
    from io import StringIO
    s = text_csv.lstrip("\ufeff")
    reader = csv.DictReader(StringIO(s))
    return [dict(row) for row in reader]

def _reports_period_function(name: str, period: str):
    path = f"reports/{name}(period='{period}')"
    csv_text = _ve_get_csv(path, version="v1.0")
    return _parse_csv(csv_text)

def report_yammer_groups_activity_counts(period: str = "D30"):
    rows = _reports_period_function("getYammerGroupsActivityCounts", period)
    s = get_session()
    try:
        for r in rows:
            report_date = r.get("Report Date") or r.get("reportDate") or r.get("report_date")
            rr = r.get("Report Refresh Date") or r.get("reportRefreshDate")
            rp = r.get("Report Period") or r.get("reportPeriod")
            liked = r.get("Liked")
            posted = r.get("Posted")
            read = r.get("Read")
            obj = s.query(VEReportGroupsActivityCounts).filter(VEReportGroupsActivityCounts.report_date == str(report_date)).first()
            if obj is None:
                obj = VEReportGroupsActivityCounts(report_date=str(report_date))
            obj.report_refresh_date = rr
            obj.report_period = str(rp) if rp is not None else None
            try:
                obj.liked = int(liked) if liked not in (None, "") else 0
            except:
                obj.liked = 0
            try:
                obj.posted = int(posted) if posted not in (None, "") else 0
            except:
                obj.posted = 0
            try:
                obj.read = int(read) if read not in (None, "") else 0
            except:
                obj.read = 0
            s.add(obj)
        s.commit()
    finally:
        s.close()
    return rows

def report_yammer_groups_activity_detail(period: str = "D30"):
    rows = _reports_period_function("getYammerGroupsActivityDetail", period)
    s = get_session()
    try:
        for r in rows:
            group_id = r.get("Group Id") or r.get("groupId")
            obj = None
            if group_id not in (None, ""):
                obj = s.query(VEReportGroupsActivityDetail).filter(VEReportGroupsActivityDetail.group_id == str(group_id)).first()
            if obj is None:
                obj = VEReportGroupsActivityDetail(group_id=str(group_id) if group_id not in (None, "") else None)
            obj.group_display_name = r.get("Group Display Name") or r.get("groupDisplayName")
            mc = r.get("Member Count")
            pc = r.get("Posted Count")
            rc = r.get("Read Count")
            lc = r.get("Liked Count")
            obj.report_refresh_date = r.get("Report Refresh Date")
            obj.report_period = str(r.get("Report Period")) if r.get("Report Period") is not None else None
            try:
                obj.member_count = int(mc) if mc not in (None, "") else 0
            except:
                obj.member_count = 0
            try:
                obj.posted_count = int(pc) if pc not in (None, "") else 0
            except:
                obj.posted_count = 0
            try:
                obj.read_count = int(rc) if rc not in (None, "") else 0
            except:
                obj.read_count = 0
            try:
                obj.liked_count = int(lc) if lc not in (None, "") else 0
            except:
                obj.liked_count = 0
            obj.last_activity_date = r.get("Group Last Activity Date") or r.get("lastActivityDate")
            s.add(obj)
        s.commit()
    finally:
        s.close()
    return rows

def report_yammer_activity_user_detail(period: str = "D30"):
    rows = _reports_period_function("getYammerActivityUserDetail", period)
    s = get_session()
    try:
        for r in rows:
            upn = r.get("User Principal Name") or r.get("userPrincipalName")
            obj = s.query(VEReportUserActivityDetail).filter(VEReportUserActivityDetail.user_principal_name == str(upn)).first() if upn not in (None, "") else None
            if obj is None:
                obj = VEReportUserActivityDetail(user_principal_name=str(upn) if upn not in (None, "") else None)
            obj.last_activity_date = r.get("Last Activity Date") or r.get("lastActivityDate")
            obj.display_name = r.get("Display Name")
            obj.user_state = r.get("User State")
            obj.state_change_date = r.get("State Change Date")
            obj.assigned_products = r.get("Assigned Products")
            obj.report_refresh_date = r.get("Report Refresh Date")
            obj.report_period = str(r.get("Report Period")) if r.get("Report Period") is not None else None
            posted = r.get("Posted")
            read = r.get("Read")
            liked = r.get("Liked")
            try:
                obj.posted = int(posted) if posted not in (None, "") else 0
            except:
                obj.posted = 0
            try:
                obj.read = int(read) if read not in (None, "") else 0
            except:
                obj.read = 0
            try:
                obj.liked = int(liked) if liked not in (None, "") else 0
            except:
                obj.liked = 0
            s.add(obj)
        s.commit()
    finally:
        s.close()
    return rows

def report_yammer_device_usage_user_detail(period: str = "D30"):
    rows = _reports_period_function("getYammerDeviceUsageUserDetail", period)
    s = get_session()
    try:
        for r in rows:
            upn = r.get("User Principal Name") or r.get("userPrincipalName")
            obj = s.query(VEReportDeviceUsageUserDetail).filter(VEReportDeviceUsageUserDetail.user_principal_name == str(upn)).first() if upn not in (None, "") else None
            if obj is None:
                obj = VEReportDeviceUsageUserDetail(user_principal_name=str(upn) if upn not in (None, "") else None)
            obj.display_name = r.get("Display Name")
            obj.user_state = r.get("User State")
            obj.state_change_date = r.get("State Change Date")
            obj.report_refresh_date = r.get("Report Refresh Date")
            obj.report_period = str(r.get("Report Period")) if r.get("Report Period") is not None else None
            obj.last_activity_date = r.get("Last Activity Date") or r.get("lastActivityDate")
            def yn(v):
                if v is None:
                    return 0
                s = str(v).strip().lower()
                if s in ("yes","true","1"):
                    return 1
                if s in ("no","false","0"):
                    return 0
                return 0
            obj.used_web = yn(r.get("Used Web") or r.get("Web"))
            obj.used_windows_phone = yn(r.get("Used Windows Phone") or r.get("Windows Phone"))
            obj.used_android_phone = yn(r.get("Used Android Phone") or r.get("Android"))
            obj.used_iphone = yn(r.get("Used iPhone") or r.get("iPhone"))
            obj.used_ipad = yn(r.get("Used iPad") or r.get("iPad"))
            obj.used_others = yn(r.get("Used Others") or r.get("Others"))
            s.add(obj)
        s.commit()
    finally:
        s.close()
    return rows

def report_yammer_activity_user_counts(period: str = "D30"):
    rows = _reports_period_function("getYammerActivityUserCounts", period)
    s = get_session()
    try:
        for r in rows:
            report_date = r.get("Report Date") or r.get("reportDate") or r.get("report_date")
            rr = r.get("Report Refresh Date")
            rp = r.get("Report Period")
            liked = r.get("Liked")
            posted = r.get("Posted")
            read = r.get("Read")
            obj = s.query(VEReportUserActivityCounts).filter(VEReportUserActivityCounts.report_date == str(report_date)).first()
            if obj is None:
                obj = VEReportUserActivityCounts(report_date=str(report_date))
            obj.report_refresh_date = rr
            obj.report_period = str(rp) if rp is not None else None
            try:
                obj.liked = int(liked) if liked not in (None, "") else 0
            except:
                obj.liked = 0
            try:
                obj.posted = int(posted) if posted not in (None, "") else 0
            except:
                obj.posted = 0
            try:
                obj.read = int(read) if read not in (None, "") else 0
            except:
                obj.read = 0
            s.add(obj)
        s.commit()
    finally:
        s.close()
    return rows
