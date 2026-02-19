from fastapi import APIRouter, HTTPException, Body, Depends
from typing import Optional
from core.db import Base, engine, get_session
from models.models_user import User
from core.auth import hash_password, verify_password, create_token, get_current_user_oauth
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()

@router.post("/register")
def register(
    name: str = Body(...), 
    email: str = Body(...), 
    password: str = Body(...), 
    role: str = Body("user"),
    current_user: User = Depends(get_current_user_oauth)
):
    """
    Registro de novo usuário (Apenas Admin).
    Parâmetros:
    - name: Nome completo.
    - email: E-mail (único).
    - password: Senha em texto (hash gerado internamente).
    - role: Perfil (user/admin).
    Retorna:
    - Dados básicos do usuário criado.
    """
    if (current_user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail={"error": "apenas administradores podem criar novos usuários"})

    s = get_session()
    try:
        existing = s.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail={"error":"email já cadastrado"})
        ph, salt = hash_password(password)
        u = User(name=name, email=email, password_hash=ph, password_salt=salt, role=role)
        s.add(u)
        s.commit()
        s.refresh(u)
        return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}
    finally:
        s.close()

@router.post("/login")
def login(email: str = Body(...), password: str = Body(...)):
    """
    Login tradicional via corpo JSON.
    Parâmetros:
    - email, password.
    Retorna:
    - access_token (Bearer) válido por 12h.
    """
    s = get_session()
    try:
        u: Optional[User] = s.query(User).filter(User.email == email).first()
        if not u:
            raise HTTPException(status_code=401, detail={"error":"credenciais inválidas"})
        if not verify_password(password, u.password_hash, u.password_salt):
            raise HTTPException(status_code=401, detail={"error":"credenciais inválidas"})
        token = create_token(u.id, expires_in=3600 * 12)
        return {"access_token": token, "token_type": "bearer"}
    finally:
        s.close()

@router.post("/token")
def token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 Password (Swagger/clients).
    Parâmetros:
    - form username (email) e password.
    Retorna:
    - access_token (Bearer) válido por 12h.
    """
    s = get_session()
    try:
        u: Optional[User] = s.query(User).filter(User.email == form_data.username).first()
        if not u:
            raise HTTPException(status_code=401, detail={"error":"credenciais inválidas"})
        if not verify_password(form_data.password, u.password_hash, u.password_salt):
            raise HTTPException(status_code=401, detail={"error":"credenciais inválidas"})
        token = create_token(u.id, expires_in=3600 * 12)
        return {"access_token": token, "token_type": "bearer"}
    finally:
        s.close()
@router.get("/me")
def me(user: User = Depends(get_current_user_oauth)):
    """
    Perfil do usuário autenticado.
    Retorna:
    - id, name, email, role.
    """
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}

@router.get("/")
def list_users(user: User = Depends(get_current_user_oauth)):
    """
    Lista usuários (apenas admin).
    Retorna:
    - Array com id, name, email, role.
    """
    if (user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail={"error":"forbidden"})
    s = get_session()
    try:
        out = []
        for u in s.query(User).all():
            out.append({"id": u.id, "name": u.name, "email": u.email, "role": u.role})
        return {"users": out}
    finally:
        s.close()

@router.delete("/{user_id}")
def delete_user(user_id: int, current_user: User = Depends(get_current_user_oauth)):
    """
    Remove um usuário pelo ID (Apenas Admin).
    Parâmetros:
    - user_id: ID do usuário a ser removido.
    Retorna:
    - Mensagem de sucesso.
    """
    if (current_user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail={"error": "apenas administradores podem remover usuários"})

    s = get_session()
    try:
        user_to_delete = s.query(User).filter(User.id == user_id).first()
        if not user_to_delete:
            raise HTTPException(status_code=404, detail={"error": "usuário não encontrado"})
        
        if user_to_delete.id == current_user.id:
            raise HTTPException(status_code=400, detail={"error": "não é permitido remover o próprio usuário logado"})

        s.delete(user_to_delete)
        s.commit()
        return {"message": f"usuário {user_id} removido com sucesso"}
    finally:
        s.close()
