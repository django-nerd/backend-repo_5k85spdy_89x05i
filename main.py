import os
from datetime import date
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import create_document, get_documents
from schemas import SwimEntry

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Swim Tracker API running"}

# Create a swim entry
@app.post("/api/swims", response_model=dict)
async def add_swim(entry: SwimEntry):
    try:
        inserted_id = create_document("swimentry", entry)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SwimSummaryResponse(BaseModel):
    total_pools: int
    from_date: str
    to_date: str
    entries: List[SwimEntry]

# Get swims within a date range and total
@app.get("/api/swims", response_model=SwimSummaryResponse)
async def get_swims(
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD inclusive"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD inclusive"),
):
    try:
        # Defaults to today if not provided
        today_str = date.today().isoformat()
        f = from_date or today_str
        t = to_date or today_str

        # MongoDB filter
        filter_dict = {"date": {"$gte": f, "$lte": t}}
        docs = get_documents("swimentry", filter_dict)

        # Convert to Pydantic models to validate
        entries: List[SwimEntry] = [SwimEntry(date=d.get("date"), pools=int(d.get("pools", 0)), note=d.get("note")) for d in docs]
        total = sum(e.pools for e in entries)

        return SwimSummaryResponse(total_pools=total, from_date=f, to_date=t, entries=entries)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
