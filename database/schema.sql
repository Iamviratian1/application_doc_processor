-- =====================================================
-- CLEAN DOCUMENT PROCESSOR DATABASE SCHEMA
-- =====================================================
-- 
-- This schema supports the three-agent document processing system:
-- 1. Document Ingestion Agent
-- 2. Data Extraction Agent  
-- 3. Data Validation Agent
--
-- =====================================================

-- =====================================================
-- 1. APPLICATIONS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id VARCHAR(255) UNIQUE NOT NULL,
    applicant_name VARCHAR(255),
    co_applicant_name VARCHAR(255),
    application_type VARCHAR(50) DEFAULT 'mortgage',
    status VARCHAR(50) DEFAULT 'document_upload',
    completion_percentage DECIMAL(5,2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    meta_data JSONB DEFAULT '{}'::jsonb
);

-- =====================================================
-- 2. DOCUMENTS TABLE (Raw Document Storage)
-- =====================================================

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id VARCHAR(255) NOT NULL REFERENCES applications(application_id),
    document_id VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    applicant_type VARCHAR(20) NOT NULL DEFAULT 'applicant' CHECK (applicant_type IN ('applicant', 'co_applicant')),
    file_size BIGINT,
    mime_type VARCHAR(100),
    storage_path VARCHAR(500),
    upload_status VARCHAR(50) DEFAULT 'uploaded',
    processing_status VARCHAR(50) DEFAULT 'pending',
    confidence DECIMAL(3,2) DEFAULT 0.0,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    meta_data JSONB DEFAULT '{}'::jsonb
);

-- =====================================================
-- 3. EXTRACTED_DATA TABLE (Agent 2 Output)
-- =====================================================

CREATE TABLE IF NOT EXISTS extracted_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id),
    application_id VARCHAR(255) NOT NULL REFERENCES applications(application_id),
    document_type VARCHAR(100) NOT NULL,
    extracted_fields JSONB NOT NULL DEFAULT '{}'::jsonb, -- All fields as JSON
    field_count INTEGER DEFAULT 0,
    average_confidence DECIMAL(3,2) DEFAULT 0.0,
    extraction_method VARCHAR(50) DEFAULT 'textract',
    raw_response JSONB, -- Full Textract response
    page_number INTEGER, -- For mortgage applications
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    agent_version VARCHAR(20) DEFAULT '1.0'
);

-- =====================================================
-- 4. VALIDATION_RESULTS TABLE (Agent 3 Output)
-- =====================================================

CREATE TABLE IF NOT EXISTS validation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id VARCHAR(255) NOT NULL REFERENCES applications(application_id),
    validation_summary JSONB NOT NULL DEFAULT '{}'::jsonb, -- All validation results as JSON
    total_fields INTEGER DEFAULT 0,
    validated_fields INTEGER DEFAULT 0,
    mismatched_fields INTEGER DEFAULT 0,
    missing_fields INTEGER DEFAULT 0,
    critical_mismatches INTEGER DEFAULT 0,
    high_mismatches INTEGER DEFAULT 0,
    medium_mismatches INTEGER DEFAULT 0,
    low_mismatches INTEGER DEFAULT 0,
    overall_validation_score DECIMAL(3,2) DEFAULT 0.0,
    flag_for_review BOOLEAN DEFAULT FALSE,
    validation_notes TEXT,
    validated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    agent_version VARCHAR(20) DEFAULT '1.0'
);

-- =====================================================
-- 5. GOLDEN_DATA TABLE (Agent 4 Output - Final Structured Data)
-- =====================================================

CREATE TABLE IF NOT EXISTS golden_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id VARCHAR(255) NOT NULL REFERENCES applications(application_id),
    golden_fields JSONB NOT NULL DEFAULT '{}'::jsonb, -- All final fields as JSON
    field_count INTEGER DEFAULT 0,
    verified_fields INTEGER DEFAULT 0,
    high_confidence_fields INTEGER DEFAULT 0,
    data_quality_score DECIMAL(3,2) DEFAULT 0.0,
    ready_for_decision_engine BOOLEAN DEFAULT FALSE,
    data_sources JSONB DEFAULT '{}'::jsonb, -- Track which documents contributed to each field
    validation_summary JSONB DEFAULT '{}'::jsonb, -- Summary of validation results
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    agent_version VARCHAR(20) DEFAULT '1.0'
);

-- =====================================================
-- 6. PROCESSING_LOGS TABLE (Audit Trail)
-- =====================================================

CREATE TABLE IF NOT EXISTS processing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id VARCHAR(255) NOT NULL REFERENCES applications(application_id),
    document_id UUID REFERENCES documents(id),
    agent_name VARCHAR(50) NOT NULL, -- 'ingestion', 'extraction', 'validation'
    step_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'started', 'completed', 'failed', 'skipped'
    message TEXT,
    error_details JSONB,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 7. DOCUMENT_JOBS TABLE (Queue Management)
-- =====================================================

CREATE TABLE IF NOT EXISTS document_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id VARCHAR(255) NOT NULL REFERENCES applications(application_id),
    document_id UUID REFERENCES documents(id),
    job_type VARCHAR(50) NOT NULL, -- 'ingestion', 'extraction', 'validation'
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    priority INTEGER DEFAULT 5,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 8. INDEXES FOR PERFORMANCE
-- =====================================================

-- Applications indexes
CREATE INDEX IF NOT EXISTS idx_applications_application_id ON applications(application_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_created_at ON applications(created_at);

-- Documents indexes
CREATE INDEX IF NOT EXISTS idx_documents_application_id ON documents(application_id);
CREATE INDEX IF NOT EXISTS idx_documents_document_id ON documents(document_id);
CREATE INDEX IF NOT EXISTS idx_documents_type_applicant ON documents(document_type, applicant_type);
CREATE INDEX IF NOT EXISTS idx_documents_processing_status ON documents(processing_status);

-- Extracted data indexes
CREATE INDEX IF NOT EXISTS idx_extracted_data_document_id ON extracted_data(document_id);
CREATE INDEX IF NOT EXISTS idx_extracted_data_application_id ON extracted_data(application_id);
CREATE INDEX IF NOT EXISTS idx_extracted_data_extracted_fields ON extracted_data USING GIN (extracted_fields);

-- Validation results indexes
CREATE INDEX IF NOT EXISTS idx_validation_results_application_id ON validation_results(application_id);
CREATE INDEX IF NOT EXISTS idx_validation_results_validation_summary ON validation_results USING GIN (validation_summary);
CREATE INDEX IF NOT EXISTS idx_validation_results_flag_review ON validation_results(flag_for_review);

-- Golden data indexes
CREATE INDEX IF NOT EXISTS idx_golden_data_application_id ON golden_data(application_id);
CREATE INDEX IF NOT EXISTS idx_golden_data_golden_fields ON golden_data USING GIN (golden_fields);

-- Processing logs indexes
CREATE INDEX IF NOT EXISTS idx_processing_logs_application_id ON processing_logs(application_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_document_id ON processing_logs(document_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_agent_name ON processing_logs(agent_name);
CREATE INDEX IF NOT EXISTS idx_processing_logs_created_at ON processing_logs(created_at);

-- Document jobs indexes
CREATE INDEX IF NOT EXISTS idx_document_jobs_application_id ON document_jobs(application_id);
CREATE INDEX IF NOT EXISTS idx_document_jobs_document_id ON document_jobs(document_id);
CREATE INDEX IF NOT EXISTS idx_document_jobs_status ON document_jobs(status);
CREATE INDEX IF NOT EXISTS idx_document_jobs_priority ON document_jobs(priority);

-- =====================================================
-- 9. TRIGGERS FOR AUTOMATIC UPDATES
-- =====================================================

-- Update applications.updated_at on any change
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_applications_updated_at 
    BEFORE UPDATE ON applications 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_golden_data_updated_at 
    BEFORE UPDATE ON golden_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 9. JSON INDEXES FOR PERFORMANCE
-- =====================================================

-- Indexes for extracted_data JSONB fields
CREATE INDEX IF NOT EXISTS idx_extracted_data_fields_gin ON extracted_data USING GIN (extracted_fields);
CREATE INDEX IF NOT EXISTS idx_extracted_data_document_type ON extracted_data (document_type);
CREATE INDEX IF NOT EXISTS idx_extracted_data_page_number ON extracted_data (page_number);

-- Indexes for validation_results JSONB fields
CREATE INDEX IF NOT EXISTS idx_validation_results_summary_gin ON validation_results USING GIN (validation_summary);

-- Indexes for golden_data JSONB fields
CREATE INDEX IF NOT EXISTS idx_golden_data_fields_gin ON golden_data USING GIN (golden_fields);
CREATE INDEX IF NOT EXISTS idx_golden_data_sources_gin ON golden_data USING GIN (data_sources);
CREATE INDEX IF NOT EXISTS idx_golden_data_validation_gin ON golden_data USING GIN (validation_summary);

-- =====================================================
-- 10. VIEWS FOR COMMON QUERIES
-- =====================================================

-- Application processing status view
CREATE OR REPLACE VIEW application_processing_status AS
SELECT 
    a.application_id,
    a.status,
    a.completion_percentage,
    COUNT(DISTINCT d.id) as total_documents,
    COUNT(DISTINCT CASE WHEN d.processing_status = 'completed' THEN d.id END) as processed_documents,
    COALESCE(SUM(ed.field_count), 0) as total_extracted_fields,
    COALESCE(SUM(vr.validated_fields), 0) as total_validated_fields,
    COALESCE(SUM(gd.field_count), 0) as total_golden_fields,
    COUNT(DISTINCT CASE WHEN vr.flag_for_review = true THEN vr.id END) as flagged_for_review
FROM applications a
LEFT JOIN documents d ON a.application_id = d.application_id
LEFT JOIN extracted_data ed ON a.application_id = ed.application_id
LEFT JOIN validation_results vr ON a.application_id = vr.application_id
LEFT JOIN golden_data gd ON a.application_id = gd.application_id
GROUP BY a.application_id, a.status, a.completion_percentage;

-- Document processing pipeline view
CREATE OR REPLACE VIEW document_processing_pipeline AS
SELECT 
    d.id as document_id,
    d.application_id,
    d.filename,
    d.document_type,
    d.processing_status,
    COALESCE(SUM(ed.field_count), 0) as extracted_fields_count,
    COUNT(DISTINCT vr.id) as validation_results_count,
    COUNT(DISTINCT gd.id) as golden_data_count,
    MAX(pl.created_at) as last_processing_activity
FROM documents d
LEFT JOIN extracted_data ed ON d.id = ed.document_id
LEFT JOIN validation_results vr ON d.application_id = vr.application_id
LEFT JOIN golden_data gd ON d.application_id = gd.application_id
LEFT JOIN processing_logs pl ON d.id = pl.document_id
GROUP BY d.id, d.application_id, d.filename, d.document_type, d.processing_status;
