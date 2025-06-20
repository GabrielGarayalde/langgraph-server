# Company Spreadsheets - Excel Integration

This directory contains Excel spreadsheets that can be accessed by both engineers and the LangGraph agent. This creates a bridge between traditional engineering workflows and AI automation.

## 🎯 **Purpose**

- **Centralized Calculations**: Company-approved calculation methods in familiar Excel format
- **Dual Access**: Engineers can edit manually, agents can read/write programmatically
- **Standardization**: Consistent calculation methods across the organization
- **Validation**: Engineers can verify AI calculations and vice versa

## 📁 **Directory Structure**

```
company_spreadsheets/
├── structural/
│   └── beam_calculations.xlsx      # Structural beam analysis
└── calculator.xlsx                 # Simple arithmetic calculator
```

## 🔧 **Available Tools**

The agent has access to these Excel tools:

### 1. `read_excel_sheet`
Read data from Excel files
```python
read_excel_sheet("calculator.xlsx", "Calculator", "A1:B10")
```

### 2. `write_excel_sheet`
Write data to Excel files
```python
write_excel_sheet("calculator.xlsx", "Calculator", "B3", 42)
```

### 3. `execute_excel_calculation`
Complete calculation workflow: input → process → output
```python
execute_excel_calculation(
    "structural/beam_calculations.xlsx",
    {"B4": 50, "B5": 8, "B6": 800},  # Load, Span, Section Modulus
    ["B9", "B10", "B14"],            # Moment, Stress, Status
    "Beam Calculations"
)
```

## 📊 **Sample Calculations**

### Calculator.xlsx
- **Purpose**: Basic arithmetic operations
- **Inputs**: B3 (Number 1), B4 (Number 2)
- **Outputs**: B6 (Sum), B7 (Product), B8 (Difference), B9 (Division)

### Beam Calculations.xlsx
- **Purpose**: Structural beam analysis per AS 4100-1998
- **Inputs**: 
  - B4: Load (kN)
  - B5: Span (m)
  - B6: Section Modulus (cm³)
- **Outputs**:
  - B9: Maximum Moment (kNm)
  - B10: Maximum Stress (MPa)
  - B11: Deflection Factor
  - B14: Status (PASS/FAIL)

## 🚀 **Usage Examples**

### Agent Usage
```python
# Calculate beam stress
result = await execute_excel_calculation(
    "structural/beam_calculations.xlsx",
    {"B4": 75, "B5": 6, "B6": 600},
    ["B9", "B10", "B14"],
    "Beam Calculations"
)
print(f"Beam status: {result['outputs']['B14']}")
```

### Human Usage
1. Navigate to `company_spreadsheets/`
2. Double-click any `.xlsx` file to open in Excel
3. Edit inputs and view results
4. Save changes for agent to access

## ⚠️ **Important Notes**

1. **File Format**: Use `.xlsx` format only
2. **Formulas**: Excel formulas are evaluated by the agent
3. **Backup**: Files are automatically saved when agent writes to them
4. **Concurrent Access**: Avoid editing files while agent is using them
5. **Dependencies**: Requires `openpyxl` package

## 🔄 **Future Enhancements**

- **Google Sheets Integration**: Real-time collaboration
- **Version Control**: Track calculation changes
- **Template Library**: Standard calculation templates
- **Validation Rules**: Input validation and error checking
- **Audit Trail**: Log of all agent interactions

## 🛠️ **Technical Details**

- **Formula Engine**: Custom Python-based Excel formula evaluator
- **Supported Functions**: Basic arithmetic, IF, SQRT, MIN, MAX
- **Cell References**: Automatic resolution of cell dependencies
- **Error Handling**: Graceful fallbacks for complex formulas

This system bridges the gap between traditional engineering spreadsheets and modern AI automation, providing the best of both worlds.
