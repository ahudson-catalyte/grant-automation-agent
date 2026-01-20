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
from typing import Dict, List
import os
import json
from datetime import datetime
import asyncio

router = APIRouter(prefix="/api/grants", tags=["grants"])

# In-memory storage (since no database)
grant_data_store: Dict[str, GrantData] = {}
generated_docs_store: Dict[str, Dict[str, str]] = {}

llm_service = LLMService()
document_service = DocumentService()


@router.post("/upload", response_model=List[UploadResponse])
async def upload_grant_letters(files: List[UploadFile] = File(...)):
    """
    Upload multiple grant acceptance letters (PDF or DOCX) at once
    """
    print("\n" + "="*60)
    print(f"📤 Receiving {len(files)} file(s) for upload")
    print("="*60)
    
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per upload")
    
    results = []
    
    for idx, file in enumerate(files, 1):
        print(f"\n{'─'*60}")
        print(f"Processing file {idx}/{len(files)}: {file.filename}")
        print(f"{'─'*60}")
        
        try:
            result = await process_single_file(file, idx, len(files))
            results.append(result)
        except HTTPException as he:
            # Add failed file to results
            results.append(UploadResponse(
                success=False,
                message=he.detail,
                file_id="",
                filename=file.filename or f"file_{idx}"
            ))
        except Exception as e:
            # Add failed file to results
            results.append(UploadResponse(
                success=False,
                message=f"Error: {str(e)}",
                file_id="",
                filename=file.filename or f"file_{idx}"
            ))
    
    successful = sum(1 for r in results if r.success)
    print(f"\n{'='*60}")
    print(f"✓ Upload complete: {successful}/{len(files)} files processed successfully")
    print(f"{'='*60}\n")
    
    return results


async def process_single_file(file: UploadFile, file_num: int, total_files: int) -> UploadResponse:
    """Process a single file upload"""
    
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    ext = os.path.splitext(file.filename)[1].lower()
    print(f"📄 File extension: {ext}")
    
    if ext not in ['.pdf', '.docx', '.doc']:
        raise HTTPException(
            status_code=400, 
            detail=f"File '{file.filename}': Only PDF and DOCX files are supported"
        )
    
    # Read file content
    print("📖 Reading file content...")
    content = await file.read()
    print(f"✓ Read {len(content)} bytes")
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail=f"File '{file.filename}' is empty")
    
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
        print(f"✓ First 150 chars: {text[:150]}")
    except Exception as e:
        print(f"❌ Text extraction error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Could not extract text from '{file.filename}': {str(e)}"
        )
    
    if not text or len(text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail=f"'{file.filename}' does not contain sufficient readable text"
        )
    
    # Extract grant data using LLM
    print(f"🤖 Extracting grant data with AI ({file_num}/{total_files})...")
    try:
        grant_data = llm_service.extract_all_data(text)
        print(f"✓ AI extraction successful for '{file.filename}'")
        
        # Store in memory
        grant_data_store[file_id] = grant_data
        
        return UploadResponse(
            success=True,
            message="File uploaded and processed successfully",
            file_id=file_id,
            filename=file.filename,
            document_type=grant_data.document_type.value if grant_data.document_type else None
        )
        
    except Exception as e:
        print(f"\n❌ ERROR during processing '{file.filename}':")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        
        # Store partial data
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
            message=f"File uploaded but AI processing incomplete: {str(e)}",
            file_id=file_id,
            filename=file.filename
        )


@router.post("/upload-batch", response_model=Dict[str, List[UploadResponse]])
async def upload_grant_letters_batch(files: List[UploadFile] = File(...)):
    """
    Upload multiple grant letters with batch processing status
    Returns detailed status for each file
    """
    print("\n" + "="*60)
    print(f"📦 BATCH UPLOAD: Processing {len(files)} file(s)")
    print("="*60)
    
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files allowed per batch upload")
    
    results = {
        "successful": [],
        "failed": [],
        "partial": []
    }
    
    for idx, file in enumerate(files, 1):
        print(f"\n{'─'*60}")
        print(f"Batch processing {idx}/{len(files)}: {file.filename}")
        print(f"{'─'*60}")
        
        try:
            result = await process_single_file(file, idx, len(files))
            
            if result.success and "incomplete" not in result.message.lower():
                results["successful"].append(result)
            elif result.success:
                results["partial"].append(result)
            else:
                results["failed"].append(result)
                
        except Exception as e:
            failed_result = UploadResponse(
                success=False,
                message=f"Processing error: {str(e)}",
                file_id="",
                filename=file.filename or f"file_{idx}"
            )
            results["failed"].append(failed_result)
    
    print(f"\n{'='*60}")
    print(f"📊 BATCH RESULTS:")
    print(f"   ✓ Successful: {len(results['successful'])}")
    print(f"   ⚠ Partial: {len(results['partial'])}")
    print(f"   ✗ Failed: {len(results['failed'])}")
    print(f"{'='*60}\n")
    
    return results


@router.post("/generate-documents-batch")
async def generate_documents_batch(file_ids: List[str], options: Dict[str, bool] = None):
    """
    Generate documents for multiple grants at once
    """
    if not file_ids or len(file_ids) == 0:
        raise HTTPException(status_code=400, detail="No file IDs provided")
    
    if len(file_ids) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 grants per batch generation")
    
    default_options = {
        'generate_workplan': True,
        'generate_budget': True,
        'generate_report_template': True,
        'generate_calendar': True,
    }
    
    if options:
        default_options.update(options)
    
    results = {
        "successful": [],
        "failed": []
    }
    
    print(f"\n📦 BATCH DOCUMENT GENERATION: {len(file_ids)} grants")
    
    for idx, file_id in enumerate(file_ids, 1):
        print(f"\nGenerating documents {idx}/{len(file_ids)} for file_id: {file_id}")
        
        try:
            if file_id not in grant_data_store:
                results["failed"].append({
                    "file_id": file_id,
                    "error": "Grant data not found"
                })
                continue
            
            grant_data = grant_data_store[file_id]
            
            generated_files = document_service.generate_all_documents(
                grant_data, 
                file_id, 
                default_options
            )
            
            # Store generated file paths
            if file_id not in generated_docs_store:
                generated_docs_store[file_id] = {}
            
            for doc_type, filepath in generated_files.items():
                if not doc_type.endswith('_error') and os.path.exists(filepath):
                    generated_docs_store[file_id][doc_type] = filepath
            
            # Build response
            file_response = {
                'file_id': file_id,
                'grant_title': grant_data.grant_title or 'Unknown',
                'files': {}
            }
            
            for doc_type, filepath in generated_files.items():
                if not doc_type.endswith('_error'):
                    filename = os.path.basename(filepath)
                    file_response['files'][doc_type] = {
                        'filename': filename,
                        'download_url': f"/api/grants/download/{file_id}/{doc_type}"
                    }
                else:
                    file_response['files'][doc_type] = filepath
            
            results["successful"].append(file_response)
            
        except Exception as e:
            print(f"❌ Error generating documents for {file_id}: {e}")
            results["failed"].append({
                "file_id": file_id,
                "error": str(e)
            })
    
    print(f"\n✓ Batch generation complete: {len(results['successful'])}/{len(file_ids)} successful\n")
    
    return results


@router.get("/data/{file_id}")
async def get_grant_data(file_id: str):
    """Retrieve extracted grant data"""
    if file_id not in grant_data_store:
        raise HTTPException(status_code=404, detail="Grant data not found")
    
    return grant_data_store[file_id]


@router.get("/list")
async def list_grants():
    """List all uploaded grants"""
    grants = []
    for file_id, grant_data in grant_data_store.items():
        grants.append({
            "file_id": file_id,
            "filename": f"grant_{file_id[:8]}.pdf",
            "organization": grant_data.organization_name,
            "grant_title": grant_data.grant_title,
            "grant_amount": grant_data.grant_amount,
            "created_at": None,
            "processed": True
        })
    
    return {"grants": grants}


@router.post("/generate-documents/{file_id}")
async def generate_documents(file_id: str, request: GenerateDocumentsRequest):
    """Generate documents for a single grant"""
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
    """Download a generated document"""
    print(f"\n📥 Download request: file_id={file_id}, doc_type={doc_type}")
    
    extensions = {
        'workplan': '.pdf',
        'budget': '.xlsx',
        'report': '.docx',
        'calendar': '.ics'
    }
    
    if doc_type not in extensions:
        raise HTTPException(status_code=400, detail=f"Invalid document type: {doc_type}")
    
    if file_id in generated_docs_store and doc_type in generated_docs_store[file_id]:
        filepath = generated_docs_store[file_id][doc_type]
        print(f"✓ Found in store: {filepath}")
    else:
        filename = f"{file_id}_{doc_type}{extensions[doc_type]}"
        filepath = os.path.join("temp_files", filename)
        print(f"⚠ Not in store, trying: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        raise HTTPException(status_code=404, detail=f"File not found: {os.path.basename(filepath)}")
    
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
    """Delete a grant and all associated documents"""
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


@router.delete("/batch")
async def delete_grants_batch(file_ids: List[str]):
    """Delete multiple grants at once"""
    results = {
        "deleted": [],
        "failed": []
    }
    
    for file_id in file_ids:
        try:
            if file_id not in grant_data_store:
                results["failed"].append({
                    "file_id": file_id,
                    "error": "Grant not found"
                })
                continue
            
            # Delete generated documents
            if file_id in generated_docs_store:
                for doc_type, filepath in generated_docs_store[file_id].items():
                    if os.path.exists(filepath):
                        os.remove(filepath)
                del generated_docs_store[file_id]
            
            # Delete from store
            del grant_data_store[file_id]
            
            # Delete original file
            temp_files = os.listdir("temp_files")
            for filename in temp_files:
                if filename.startswith(file_id):
                    filepath = os.path.join("temp_files", filename)
                    if os.path.exists(filepath):
                        os.remove(filepath)
            
            results["deleted"].append(file_id)
            
        except Exception as e:
            results["failed"].append({
                "file_id": file_id,
                "error": str(e)
            })
    
    return results


@router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "service": "grant-automation-api"}