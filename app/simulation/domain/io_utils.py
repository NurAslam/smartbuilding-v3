import io
import pandas as pd
from fastapi import UploadFile, HTTPException


def read_csv_upload_and_bytes(file: UploadFile) -> (pd.DataFrame, bytes):
    if file is None:
        raise HTTPException(status_code=400, detail="CSV file is required.")
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be .csv")
    try:
        content = file.file.read()
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca CSV: {e}")
    return df, content
