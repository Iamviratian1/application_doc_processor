#!/usr/bin/env python3
"""
Check database contents to see what documents and extracted data we have
"""

import asyncio
import asyncpg
import json

async def check_database():
    # Connect to database
    conn = await asyncpg.connect("postgresql://postgres:postgres123@localhost:5432/document_processor")
    
    print("=== APPLICATIONS ===")
    apps = await conn.fetch("SELECT application_id, applicant_name, created_at FROM applications ORDER BY created_at DESC LIMIT 5")
    for app in apps:
        print(f"App ID: {app['application_id']}, Name: {app['applicant_name']}, Created: {app['created_at']}")
    
    print("\n=== DOCUMENTS ===")
    docs = await conn.fetch("SELECT application_id, filename, document_type, processing_status, uploaded_at FROM documents ORDER BY uploaded_at DESC LIMIT 10")
    for doc in docs:
        print(f"App: {doc['application_id']}, File: {doc['filename']}, Type: {doc['document_type']}, Status: {doc['processing_status']}, Uploaded: {doc['uploaded_at']}")
    
    print("\n=== EXTRACTED DATA ===")
    extracted = await conn.fetch("SELECT application_id, document_type, field_count, extracted_at FROM extracted_data ORDER BY extracted_at DESC LIMIT 10")
    for ext in extracted:
        print(f"App: {ext['application_id']}, Type: {ext['document_type']}, Fields: {ext['field_count']}, Extracted: {ext['extracted_at']}")
    
    print("\n=== EXTRACTED FIELDS DETAILS ===")
    # Get the most recent extracted data with field details
    recent_extracted = await conn.fetch("SELECT application_id, document_type, extracted_fields FROM extracted_data ORDER BY extracted_at DESC LIMIT 3")
    for ext in recent_extracted:
        print(f"\nApp: {ext['application_id']}, Type: {ext['document_type']}")
        if ext['extracted_fields']:
            fields = ext['extracted_fields']
            if isinstance(fields, list):
                for field in fields:
                    print(f"  - {field.get('field_name', 'unknown')}: {field.get('field_value', 'unknown')}")
            else:
                print(f"  Raw fields: {fields}")
        else:
            print("  No fields extracted")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_database())
