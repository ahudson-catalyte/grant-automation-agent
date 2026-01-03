from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.models.schemas import (
    UploadResponse, 
    GenerateDocumentsRequest,
    GrantData
)
from app.services.llm_service import LLMService
from app.services.document_service import DocumentService
from app.utils.file_helpers import (
    save_uploaded_file,
    extract_text_from_file,
    generate_file_id
)
from typing import Dict
import os
import json
from datetime import datetime

router = APIRouter(prefix="/api/grants", tags=["grants"])

# In-memory storage (since no database)
grant_data_store: Dict[str, GrantData] = {}
generated_docs_store: Dict[str, Dict[str, str]] = {}  # file_id -> {doc_type -> filepath}

llm_service = LLMService()
document_service = DocumentService()


@router.post("/upload", response_model=UploadResponse)
async def upload_grant_letter(file: UploadFile = File(...)):
    """
    Upload a grant acceptance letter (PDF or DOCX)
    """
    print("\n" + "="*60)
    print("📤 Receiving file upload:", file.filename)
    print("="*60)
    
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    ext = os.path.splitext(file.filename)[1].lower()
    print(f"📄 File extension: {ext}")
    
    if ext not in ['.pdf', '.docx', '.doc']:
        raise HTTPException(
            status_code=400, 
            detail="Only PDF and DOCX files are supported"
        )
    
    try:
        # Read file content
        print("📖 Reading file content...")
        content = await file.read()
        print(f"✓ Read {len(content)} bytes")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Generate file ID
        file_id = generate_file_id()
        
        # Save file
        print("💾 Saving file...")
        filepath = save_uploaded_file(content, file.filename, file_id)
        print(f"✓ Saved to: {filepath}")
        print(f"✓ File ID: {file_id}")
        
        # Extract text
        print("🔍 Extracting text...")
        try:
            text, file_type = extract_text_from_file(filepath)
            print(f"✓ Extracted {len(text)} characters")
            print(f"✓ First 200 chars: {text[:200]}")
        except Exception as e:
            print(f"❌ Text extraction error: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract text from file: {str(e)}"
            )
        
        if not text or len(text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Could not extract sufficient text from file. Please ensure the file contains readable text."
            )
        
        # Extract grant data using LLM
        print("🤖 Extracting grant data with LLM...")
        try:
            grant_data = llm_service.extract_all_data(text)
            print("✓ LLM extraction successful")
            
            # Store in memory
            grant_data_store[file_id] = grant_data
            
            return UploadResponse(
                success=True,
                message="File uploaded and processed successfully",
                file_id=file_id,
                filename=file.filename
            )
            
        except Exception as e:
            print(f"\n❌ ERROR during upload:")
            print("="*60)
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            
            # Print full traceback for debugging
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
            print("="*60 + "\n")
            
            # Store partial data (text only) so we can still access it
            from app.models.schemas import Timeline, Budget, WorkPlan
            partial_grant_data = GrantData(
                raw_text=text,
                organization_name=None,
                grant_title=None,
                grant_amount=None,
                grant_period=None,
                funder_name=None,
                timeline=None,
                budget=None,
                workplan=None
            )
            grant_data_store[file_id] = partial_grant_data
            
            return UploadResponse(
                success=True,
                message=f"File uploaded but processing incomplete: {str(e)}",
                file_id=file_id,
                filename=file.filename
            )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.get("/data/{file_id}")
async def get_grant_data(file_id: str):
    """
    Retrieve extracted grant data
    """
    if file_id not in grant_data_store:
        raise HTTPException(status_code=404, detail="Grant data not found")
    
    return grant_data_store[file_id]


@router.get("/list")
async def list_grants():
    """
    List all uploaded grants
    """
    grants = []
    for file_id, grant_data in grant_data_store.items():
        grants.append({
            "file_id": file_id,
            "filename": f"grant_{file_id[:8]}.pdf",  # Simplified since we don't store filename
            "organization": grant_data.organization_name,
            "grant_title": grant_data.grant_title,
            "grant_amount": grant_data.grant_amount,
            "created_at": None,
            "processed": True
        })
    
    return {"grants": grants}


@router.post("/generate-documents/{file_id}")
async def generate_documents(file_id: str, request: GenerateDocumentsRequest):
    """
    Generate all requested documents from extracted grant data
    """
    if file_id not in grant_data_store:
        raise HTTPException(status_code=404, detail="Grant data not found")
    
    grant_data = grant_data_store[file_id]
    
    try:
        options = {
            'generate_workplan': request.generate_workplan,
            'generate_budget': request.generate_budget,
            'generate_report_template': request.generate_report_template,
            'generate_calendar': request.generate_calendar,
        }
        
        generated_files = document_service.generate_all_documents(
            grant_data, 
            file_id, 
            options
        )
        
        # Store generated file paths
        if file_id not in generated_docs_store:
            generated_docs_store[file_id] = {}
        
        for doc_type, filepath in generated_files.items():
            if not doc_type.endswith('_error') and os.path.exists(filepath):
                generated_docs_store[file_id][doc_type] = filepath
        
        # Return file paths/URLs
        response = {
            'success': True,
            'files': {}
        }
        
        for doc_type, filepath in generated_files.items():
            if not doc_type.endswith('_error'):
                filename = os.path.basename(filepath)
                response['files'][doc_type] = {
                    'filename': filename,
                    'download_url': f"/api/grants/download/{file_id}/{doc_type}"
                }
            else:
                response['files'][doc_type] = filepath
        
        return response
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error generating documents: {str(e)}"
        )


@router.get("/download/{file_id}/{doc_type}")
async def download_document(file_id: str, doc_type: str):
    """
    Download a generated document
    """
    print(f"\n📥 Download request: file_id={file_id}, doc_type={doc_type}")
    
    # Map doc_type to file extension
    extensions = {
        'workplan': '.pdf',
        'budget': '.xlsx',
        'report': '.docx',
        'calendar': '.ics'
    }
    
    if doc_type not in extensions:
        raise HTTPException(status_code=400, detail=f"Invalid document type: {doc_type}")
    
    # Try to get from stored paths first
    if file_id in generated_docs_store and doc_type in generated_docs_store[file_id]:
        filepath = generated_docs_store[file_id][doc_type]
        print(f"✓ Found in store: {filepath}")
    else:
        # Fallback: construct expected filename
        filename = f"{file_id}_{doc_type}{extensions[doc_type]}"
        filepath = os.path.join("temp_files", filename)
        print(f"⚠ Not in store, trying: {filepath}")
    
    print(f"📂 Checking file: {filepath}")
    print(f"📂 File exists: {os.path.exists(filepath)}")
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        print(f"📂 Contents of temp_files:")
        if os.path.exists("temp_files"):
            for f in os.listdir("temp_files"):
                print(f"  - {f}")
        raise HTTPException(status_code=404, detail=f"File not found: {os.path.basename(filepath)}")
    
    # Determine media type
    media_types = {
        '.pdf': 'application/pdf',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.ics': 'text/calendar'
    }
    
    ext = extensions[doc_type]
    media_type = media_types.get(ext, 'application/octet-stream')
    
    print(f"✓ Sending file with media_type: {media_type}")
    
    return FileResponse(
        path=filepath,
        media_type=media_type,
        filename=os.path.basename(filepath),
        headers={
            "Content-Disposition": f'attachment; filename="{os.path.basename(filepath)}"'
        }
    )


@router.delete("/{file_id}")
async def delete_grant(file_id: str):
    """
    Delete a grant and all associated documents
    """
    if file_id not in grant_data_store:
        raise HTTPException(status_code=404, detail="Grant not found")
    
    # Delete generated documents
    if file_id in generated_docs_store:
        for doc_type, filepath in generated_docs_store[file_id].items():
            if os.path.exists(filepath):
                os.remove(filepath)
        del generated_docs_store[file_id]
    
    # Delete from store
    del grant_data_store[file_id]
    
    # Try to delete original file
    temp_files = os.listdir("temp_files")
    for filename in temp_files:
        if filename.startswith(file_id):
            filepath = os.path.join("temp_files", filename)
            if os.path.exists(filepath):
                os.remove(filepath)
    
    return {"success": True, "message": "Grant deleted successfully"}


@router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "service": "grant-automation-api"}