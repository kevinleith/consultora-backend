from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, validator
import sqlite3
from datetime import datetime, timezone
import os
from pathlib import Path
import re

app = FastAPI()

# CORS Configuration
# Para producción: especificar origins exactos
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1",
        "http://localhost",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "*"  # Comentar en producción
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Configuration
DB_FILE = Path(__file__).parent / "leads.db"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "devtoken")

# Models
class Lead(BaseModel):
    nombre: str
    email: EmailStr
    empresa: str

    @validator('nombre', 'empresa')
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Campo no puede estar vacío')
        return v.strip()

# Database Functions
def get_db_connection():
    """Retorna una conexión a la base de datos"""
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn

def create_table_if_not_exists():
    """Crea la tabla de leads si no existe"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            empresa TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_lead(lead: Lead, ip_address: str, user_agent: str):
    """Guarda un lead en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    
    try:
        cursor.execute('''
            INSERT INTO leads (nombre, email, empresa, ip_address, user_agent, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (lead.nombre, lead.email, lead.empresa, ip_address, user_agent, timestamp_utc))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_all_leads(limit: int = 50):
    """Obtiene los últimos leads de la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, nombre, email, empresa, ip_address, user_agent, timestamp
        FROM leads
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    
    leads = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in leads]

# Initialize Database
create_table_if_not_exists()

# Endpoints
@app.post("/lead")
async def create_lead(lead: Lead, request: Request):
    """Crea un nuevo lead y lo guarda en SQLite"""
    # Obtener IP del cliente
    client_ip = request.client.host if request.client else "unknown"
    
    # Obtener User-Agent
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Guardar el lead
    saved = save_lead(lead, client_ip, user_agent)
    
    if not saved:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    return {"ok": True}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True}

@app.get("/admin/leads")
async def get_leads(x_admin_token: str = Header(None)):
    """Obtiene los últimos 50 leads (requiere token de admin)"""
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    leads = get_all_leads(50)
    return {"ok": True, "data": leads, "count": len(leads)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
