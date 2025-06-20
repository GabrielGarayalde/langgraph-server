#!/usr/bin/env python3
"""
Simple test for Excel integration functionality.
"""

import asyncio
import sys
import os

# Add the src directory to the path so we can import our tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from react_agent.tools import (
    list_excel_files,
    read_excel_sheet,
    write_excel_sheet,
    execute_excel_calculation
)

async def simple_test():
    """Simple test of Excel integration."""
    
    print("Testing Excel Integration\n")
    
    # 1. List files
    print("1. Listing Excel files...")
    files_result = await list_excel_files.ainvoke({})
    print(f"Found {files_result.get('count', 0)} files\n")
    
    # 2. Write test values to calculator
    print("2. Testing simple calculation...")
    await write_excel_sheet.ainvoke({
        "file_path": "calculator.xlsx",
        "sheet_name": "Calculator", 
        "cell_range": "B3",
        "data": 10
    })
    
    await write_excel_sheet.ainvoke({
        "file_path": "calculator.xlsx",
        "sheet_name": "Calculator",
        "cell_range": "B4", 
        "data": 5
    })
    
    # Read the formulas to show what's there
    results = await read_excel_sheet.ainvoke({
        "file_path": "calculator.xlsx",
        "sheet_name": "Calculator",
        "cell_range": "B6:B9"
    })
    
    print("Results after writing 10 and 5:")
    for i, formula in enumerate(results['data']):
        operations = ['Sum', 'Product', 'Difference', 'Division']
        print(f"  {operations[i]}: {formula[0]}")
    print()
    
    # 3. Execute calculation to get actual values
    print("3. Testing calculation execution...")
    calc_result = await execute_excel_calculation.ainvoke({
        "file_path": "calculator.xlsx",
        "input_data": {"B3": 20, "B4": 4},
        "output_cells": ["B6", "B7", "B8", "B9"],
        "sheet_name": "Calculator"
    })
    
    if calc_result['type'] == 'excel_calculation_success':
        print(f"Calculation with 20 and 4:")
        print(f"  Inputs: {calc_result['inputs']}")
        print(f"  Outputs: {calc_result['outputs']}")
    else:
        print(f"Error: {calc_result.get('error', 'Unknown error')}")
    
    print("\nExcel integration test completed!")

if __name__ == "__main__":
    asyncio.run(simple_test())
