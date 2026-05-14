from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional
from app.database import get_db_connection
import uuid

router = APIRouter()

# --- PUBLIC ENDPOINTS ---

@router.get("/questions")
async def get_questions(featured: bool = False, category: Optional[str] = None):
    """Get all questions with optional filters."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = "SELECT * FROM oar_questions WHERE is_active = TRUE"
    params = []
    
    if featured:
        query += " AND is_featured = TRUE"
    
    if category:
        query += " AND category_id = %s"
        params.append(category)
        
    query += " ORDER BY created_at DESC"
    
    if featured:
        query += " LIMIT 6"
        
    cur.execute(query, params)
    questions = cur.fetchall()
    cur.close()
    conn.close()
    return questions

@router.get("/questions/{question_id}")
async def get_question(question_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM oar_questions WHERE id = %s", (question_id,))
    question = cur.fetchone()
    cur.close()
    conn.close()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@router.post("/questions/{question_id}/view")
async def increment_view(question_id: str, request: Request):
    """
    Increments view count for a question.
    In a real scenario, we'd check IP/Session for 'unique' visits.
    For this prototype, we'll do a simple increment.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE oar_questions SET view_count = view_count + 1 WHERE id = %s", (question_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "success"}

@router.get("/categories")
async def get_categories():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM oar_categories ORDER BY linea ASC")
    categories = cur.fetchall()
    cur.close()
    conn.close()
    return categories

@router.get("/countries")
async def get_countries():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM oar_countries ORDER BY name ASC")
    countries = cur.fetchall()
    cur.close()
    conn.close()
    return countries

@router.get("/cifras")
async def get_cifras(category: Optional[str] = None, country: Optional[str] = None):
    conn = get_db_connection()
    cur = conn.cursor()
    query = "SELECT * FROM oar_cifras WHERE 1=1"
    params = []
    if category:
        query += " AND category_id = %s"
        params.append(category)
    if country:
        query += " AND country_code = %s"
        params.append(country)
    
    cur.execute(query, params)
    cifras = cur.fetchall()
    cur.close()
    conn.close()
    return cifras

@router.get("/layers")
async def get_layers():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM oar_map_layers")
    layers = cur.fetchall()
    cur.close()
    conn.close()
    return layers

@router.get("/documents")
async def get_documents(category: Optional[str] = None, country: Optional[str] = None):
    conn = get_db_connection()
    cur = conn.cursor()
    query = "SELECT * FROM oar_documents WHERE 1=1"
    params = []
    if category:
        query += " AND %s = ANY(axes)"
        params.append(category)
    if country:
        query += " AND country = %s"
        params.append(country)
    
    cur.execute(query, params)
    docs = cur.fetchall()
    cur.close()
    conn.close()
    return docs

@router.get("/view-guides")
async def get_view_guides():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM oar_view_guides")
    guides = cur.fetchall()
    cur.close()
    conn.close()
    return guides

@router.get("/indicators")
async def get_indicators():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM oar_indicators")
    indicators = cur.fetchall()
    # Fetch metrics for each
    results = []
    for ind in indicators:
        cur.execute("SELECT * FROM oar_metrics WHERE indicator_id = %s", (ind['id'],))
        ind['metrics'] = cur.fetchall()
        results.append(ind)
    cur.close()
    conn.close()
    return results

# --- MAINTAINER ENDPOINTS (CRUD) ---
# As requested, these are public for now.

@router.post("/maintainer/questions")
async def upsert_question(data: dict):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Simple UPSERT logic
    query = """
    INSERT INTO oar_questions (id, category_id, question, short_question, description, highlight, path, icon, color, is_featured, is_active)
    VALUES (%(id)s, %(category_id)s, %(question)s, %(short_question)s, %(description)s, %(highlight)s, %(path)s, %(icon)s, %(color)s, %(is_featured)s, %(is_active)s)
    ON CONFLICT (id) DO UPDATE SET
        category_id = EXCLUDED.category_id,
        question = EXCLUDED.question,
        short_question = EXCLUDED.short_question,
        description = EXCLUDED.description,
        highlight = EXCLUDED.highlight,
        path = EXCLUDED.path,
        icon = EXCLUDED.icon,
        color = EXCLUDED.color,
        is_featured = EXCLUDED.is_featured,
        is_active = EXCLUDED.is_active,
        updated_at = NOW()
    RETURNING *;
    """
    cur.execute(query, data)
    new_q = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return new_q

@router.delete("/maintainer/questions/{question_id}")
async def delete_question(question_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM oar_questions WHERE id = %s", (question_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "deleted"}

@router.post("/maintainer/documents")
async def upsert_document(data: dict):
    conn = get_db_connection()
    cur = conn.cursor()
    import json
    
    # Ensure versions is JSON string if it's a list
    if isinstance(data.get('versions'), list):
        data['versions'] = json.dumps(data['versions'])

    query = """
    INSERT INTO oar_documents (id, name, description, source, axes, type, date, country, author, download_url, thumbnail, versions)
    VALUES (%(id)s, %(name)s, %(description)s, %(source)s, %(axes)s, %(type)s, %(date)s, %(country)s, %(author)s, %(download_url)s, %(thumbnail)s, %(versions)s)
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        description = EXCLUDED.description,
        source = EXCLUDED.source,
        axes = EXCLUDED.axes,
        type = EXCLUDED.type,
        date = EXCLUDED.date,
        country = EXCLUDED.country,
        author = EXCLUDED.author,
        download_url = EXCLUDED.download_url,
        thumbnail = EXCLUDED.thumbnail,
        versions = EXCLUDED.versions,
        updated_at = NOW()
    RETURNING *;
    """
    cur.execute(query, data)
    new_doc = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return new_doc

@router.delete("/maintainer/documents/{doc_id}")
async def delete_document(doc_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM oar_documents WHERE id = %s", (doc_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"status": "deleted"}
