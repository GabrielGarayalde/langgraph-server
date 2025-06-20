#!/usr/bin/env python3
"""
Test script for Excel integration tools.
"""

import asyncio
import sys
import os

# Add the src directory to the path so we can import the tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from react_agent.tools import (
    list_excel_files,
    read_excel_sheet,
    write_excel_sheet,
    execute_excel_calculation
)

async def test_excel_tools():
    """Test all Excel integration tools."""
    
    print("=== EXCEL TOOLS TEST ===\n")
    
    # Test 1: List available Excel files
    print("1. Testing list_excel_files...")
    try:
        files_result = await list_excel_files.ainvoke({})
        print(f"Found files: {files_result}")
        print()
    except Exception as e:
        print(f"Error listing files: {e}")
        return
    
    # Test 2: Read from calculator
    print("2. Testing read_excel_sheet on calculator...")
    try:
        calc_data = await read_excel_sheet.ainvoke({
            "file_path": "calculator.xlsx",
            "sheet_name": "Calculator", 
            "cell_range": "A1:B9"
        })
        print(f"Calculator data: {calc_data}")
        print()
    except Exception as e:
        print(f"Error reading calculator: {e}")
    
    # Test 3: Write to calculator and read results
    print("3. Testing write_excel_sheet...")
    try:
        # Write some test values
        write_result1 = await write_excel_sheet.ainvoke({
            "file_path": "calculator.xlsx",
            "sheet_name": "Calculator",
            "cell_range": "B3",
            "data": 15
        })
        print(f"Write result 1: {write_result1}")
        
        write_result2 = await write_excel_sheet.ainvoke({
            "file_path": "calculator.xlsx", 
            "sheet_name": "Calculator",
            "cell_range": "B4",
            "data": 3
        })
        print(f"Write result 2: {write_result2}")
        
        # Read the results
        results = await read_excel_sheet.ainvoke({
            "file_path": "calculator.xlsx",
            "sheet_name": "Calculator",
            "cell_range": "B6:B9"
        })
        print(f"Calculation results: {results}")
        print()
    except Exception as e:
        print(f"Error in write/read test: {e}")
    
    # Test 4: Execute beam calculation
    print("4. Testing execute_excel_calculation on beam calculations...")
    try:
        beam_result = await execute_excel_calculation.ainvoke({
            "file_path": "structural/beam_calculations.xlsx",
            "input_data": {
                "B4": 25,  # Load: 25 kN
                "B5": 8,   # Span: 8 m
                "B6": 800  # Section Modulus: 800 cm³
            },
            "output_cells": ["B9", "B10", "B11", "B14"],
            "sheet_name": "Beam Calculations"
        })
        print(f"Beam calculation result: {beam_result}")
        print()
    except Exception as e:
        print(f"Error in beam calculation: {e}")
    
    # Test 5: Execute calculator calculation
    print("5. Testing execute_excel_calculation on calculator...")
    try:
        calc_result = await execute_excel_calculation.ainvoke({
            "file_path": "calculator.xlsx",
            "input_data": {
                "B3": 100,
                "B4": 7
            },
            "output_cells": ["B6", "B7", "B8", "B9"],
            "sheet_name": "Calculator"
        })
        print(f"Calculator result: {calc_result}")
        print()
    except Exception as e:
        print(f"Error in calculator execution: {e}")
    
    print("=== TEST COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(test_excel_tools())
