# Data Validation Process

## Overview

The Clean Document Processor extracts data from BOTH application forms AND documents, then compares them for validation. This document explains how the validation process works.

## Process Flow

```
1. Application Form Data → Extract Fields
2. Document Data → Extract Fields (via AWS Textract)
3. Compare Application Form vs Document Data
4. Flag Matches/Mismatches (Green/Red)
5. Store Results in Golden Table
```

## Data Sources

### Application Form Data
- **Source**: User-filled application form
- **Fields**: Personal info, financial info, employment details
- **Example**: `{"applicant_first_name": "John", "annual_income": "75000"}`

### Document Data
- **Source**: Uploaded documents (T4, Bank Statement, etc.)
- **Extraction**: AWS Textract with specific queries
- **Example**: `{"employee_name": "John Smith", "gross_income": "75000"}`

## Field Mapping

The system maps fields from different sources to standardized names for comparison:

```yaml
APPLICANT_FIRST_NAME:
  application_form_field: "applicant_first_name"
  document_fields: ["applicant_first_name", "employee_name", "policy_holder"]
  comparison_type: "text"

ANNUAL_INCOME:
  application_form_field: "annual_income"
  document_fields: ["annual_income", "gross_income", "annual_salary"]
  comparison_type: "currency"
```

## Validation Rules

### Critical Fields (Exact Match Required)
- **APPLICANT_FIRST_NAME** - Must match exactly
- **APPLICANT_LAST_NAME** - Must match exactly
- **APPLICANT_DOB** - Must match exactly
- **APPLICANT_SIN** - Must match exactly
- **ANNUAL_INCOME** - Must match within 2% tolerance

### Important Fields (Tolerance Allowed)
- **APPLICANT_ADDRESS** - 80% similarity
- **EMPLOYMENT_STATUS** - 80% similarity
- **EMPLOYER_NAME** - 80% similarity
- **CREDIT_SCORE** - 5% tolerance

### Optional Fields (Nice to Have)
- **APPLICANT_PHONE** - 80% similarity
- **APPLICANT_EMAIL** - 90% similarity
- **ACCOUNT_HOLDER** - 80% similarity
- **BANK_BALANCE** - 5% tolerance

## Comparison Types

### Text Comparison
- **Method**: Fuzzy string matching
- **Tolerance**: 0.8 (80% similarity)
- **Example**: "John Smith" vs "John A. Smith" = 85% match ✅

### Currency Comparison
- **Method**: Percentage difference
- **Tolerance**: 5% for most, 2% for critical
- **Example**: $75,000 vs $76,500 = 2% difference ✅

### Date Comparison
- **Method**: Exact match
- **Tolerance**: Exact
- **Example**: "1990-01-15" vs "1990-01-15" = Match ✅

### Number Comparison
- **Method**: Percentage difference
- **Tolerance**: 5%
- **Example**: 750 vs 780 = 4% difference ✅

## Validation Results

### Green Flags (✅)
- **Exact Match**: Values match exactly
- **Within Tolerance**: Values within allowed tolerance
- **High Similarity**: Text similarity above threshold

### Red Flags (❌)
- **Mismatch**: Values don't match within tolerance
- **Missing Data**: No document data found for field
- **Format Error**: Unable to parse or compare values

## Example Validation

### Scenario: Annual Income Validation

**Application Form**: `"annual_income": "75000"`

**T4 Document**: `"gross_income": "76500"`

**Comparison**:
1. Extract: Application = $75,000, Document = $76,500
2. Calculate: Difference = $1,500 (2% of $75,000)
3. Check: 2% < 5% tolerance ✅
4. Result: **GREEN FLAG** - Within tolerance

### Scenario: Name Mismatch

**Application Form**: `"applicant_first_name": "John"`

**Employment Letter**: `"employee_name": "Jonathan"`

**Comparison**:
1. Extract: Application = "John", Document = "Jonathan"
2. Calculate: Similarity = 60%
3. Check: 60% < 80% threshold ❌
4. Result: **RED FLAG** - Below similarity threshold

## Golden Table Structure

The final golden table contains:

```sql
golden_data:
  - field_name: "APPLICANT_FIRST_NAME"
  - application_value: "John"
  - document_value: "John"
  - validation_status: "validated"
  - confidence_score: 0.95
  - flag_color: "green"
```

## Benefits

1. **Data Integrity**: Ensures application data matches supporting documents
2. **Fraud Detection**: Identifies discrepancies that may indicate fraud
3. **Quality Assurance**: Validates data accuracy before decision engine
4. **Audit Trail**: Complete record of validation process
5. **Automated Review**: Reduces manual review workload

## Configuration

All validation rules can be modified in `config/documents.yaml`:

- **Field mappings**: Which fields to compare
- **Tolerance levels**: How strict the comparison should be
- **Field priorities**: Critical vs important vs optional
- **Comparison types**: Text, currency, date, number

This approach ensures that both application form data and document data are extracted and compared systematically, providing a comprehensive validation process.
