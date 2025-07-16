#!/usr/bin/env python3
"""
Test the timber strength calculator and provide Google Sheets structure.
"""

import sys
from pathlib import Path
import json

# Add the src directory to the path
backend_dir = Path(__file__).parent
src_dir = backend_dir / 'src'
sys.path.insert(0, str(src_dir))

def print_sheets_structure():
    """Print the recommended Google Sheets structure for the timber calculator."""
    print("AS 1720.1 TIMBER BEAM CALCULATOR - GOOGLE SHEETS STRUCTURE")
    print("=" * 70)
    print()
    
    print("SHEET LAYOUT:")
    print("Cell | Parameter | Description | Example Value")
    print("-" * 70)
    
    # Input section
    print("INPUTS:")
    print("B1   | Header           | AS 1720.1 Timber Beam Calculator | (header)")
    print("B2   | Beam Width (mm)  | Cross-section width               | 90")
    print("B3   | Beam Depth (mm)  | Cross-section depth               | 190")
    print("B4   | f'b (MPa)        | Characteristic bending strength   | 42")
    print("B5   | App Category     | Application category (1, 2, or 3)| 1")
    print("B6   | Load Duration    | Duration in years (5s=0, 50y=50) | 50")
    print("B7   | k4 Factor        | Modification factor k4            | 1.0")
    print("B8   | k6 Factor        | Modification factor k6            | 1.0")
    print("B9   | k9 Factor        | Modification factor k9            | 1.0")
    print("B10  | k12 Stability    | Stability factor k12              | 1.0")
    print()
    
    # Output section  
    print("OUTPUTS:")
    print("B13  | Section Modulus  | Z = bd²/6 (mm³)                   | =B2*B3^2/6")
    print("B14  | Capacity Factor  | φ based on category               | =IF(B5=1,0.95,IF(B5=2,0.85,0.75))")
    print("B15  | k1 Duration      | Duration factor from AS 1720.1    | =IF(B6>=50,0.57,IF(B6>=0.42,0.8,IF(B6>=0.014,0.94,1)))")
    print("B16  | Design Capacity  | Md = φ×k1×k4×k6×k9×k12×f'b×Z (Nmm)| =B14*B15*B7*B8*B9*B10*B4*B13*1000000")
    print("B17  | Utilization      | M*/Md ratio (input required)      | =(input M* here)/B16")
    print("B18  | Classification   | Beam adequacy assessment          | =IF(B17<=1,\"ADEQUATE\",\"INADEQUATE\")")
    print()
    
    print("FORMULAS BREAKDOWN:")
    print("- Section Modulus (Z): For rectangular sections = bd²/6")
    print("- Capacity Factor (φ): Category 1=0.95, Category 2=0.85, Category 3=0.75")
    print("- Duration Factor (k1): 50+years=0.57, 5months=0.8, 5days=0.94, 5sec=1.0")
    print("- Design Capacity: Md = φ × k1 × k4 × k6 × k9 × k12 × f'b × Z")
    print()
    
    print("F-GRADE EXAMPLES (f'b values from Table H2.1):")
    print("F17 Hardwood: f'b = 42 MPa")
    print("F14 Hardwood: f'b = 36 MPa") 
    print("F11 Hardwood: f'b = 31 MPa")
    print("F27 Hardwood: f'b = 67 MPa")
    print()

def test_timber_calculator():
    """Test the timber strength calculator with realistic values."""
    print("TESTING TIMBER STRENGTH CALCULATOR")
    print("=" * 50)
    
    try:
        from react_agent.sheets_tool import sheets_calculate
        
        # Test with F17 hardwood beam (90x190mm, house application, long-term load)
        test_inputs = {
            "beam_width": 90,
            "beam_depth": 190,
            "f_b_prime": 42,  # F17 hardwood from Table H2.1
            "application_category": 1,  # Category 1 (house construction)
            "load_duration": 50,  # 50+ years (permanent load)
            "k4_factor": 1.0,   # Standard case
            "k6_factor": 1.0,   # Standard case
            "k9_factor": 1.0,   # Standard case
            "k12_stability": 1.0  # Adequately restrained beam
        }
        
        print("Input parameters:")
        print(f"  Beam dimensions: {test_inputs['beam_width']}mm x {test_inputs['beam_depth']}mm")
        print(f"  f'b (F17 hardwood): {test_inputs['f_b_prime']} MPa")
        print(f"  Application: Category {test_inputs['application_category']} (house)")
        print(f"  Load duration: {test_inputs['load_duration']} years (permanent)")
        print(f"  Modification factors: k4={test_inputs['k4_factor']}, k6={test_inputs['k6_factor']}, k9={test_inputs['k9_factor']}, k12={test_inputs['k12_stability']}")
        
        print("\\nRunning calculation...")
        result = sheets_calculate.invoke({
            "calculator_name": "timber_strength",
            "inputs": test_inputs
        })
        
        if 'error' not in result:
            print("SUCCESS! Results:")
            results = result['results']
            
            # Convert section modulus from mm³ to more readable format
            z_mm3 = results.get('section_modulus', 0)
            z_cm3 = z_mm3 / 1000 if z_mm3 else 0
            
            # Convert design capacity from N·mm to kN·m
            md_nmm = results.get('design_capacity_md', 0)
            md_knm = md_nmm / 1000000 if md_nmm else 0
            
            print(f"  Section modulus (Z): {z_mm3:,.0f} mm³ ({z_cm3:,.1f} cm³)")
            print(f"  Capacity factor (φ): {results.get('capacity_factor')}")
            print(f"  Duration factor (k1): {results.get('k1_duration')}")
            print(f"  Design capacity (Md): {md_knm:.1f} kN·m")
            print(f"  Utilization ratio: {results.get('utilization_ratio', 'N/A')}")
            print(f"  Classification: {results.get('beam_classification', 'N/A')}")
            print(f"\\nSheet URL: {result['sheet_url']}")
            
            # Provide context
            print("\\nINTERPRETATION:")
            print(f"  This F17 hardwood beam can resist up to {md_knm:.1f} kN·m of bending moment")
            print(f"  For comparison, a 5kN/m load over 6m span creates {5*6**2/8:.1f} kN·m")
            
        else:
            print(f"ERROR: {result['error']}")
            print("\\nNext steps:")
            print("  1. Set up the Google Sheets calculator using the structure above")
            print("  2. Ensure the sheet ID matches the config file")
            print("  3. Test with the provided formulas")
            
    except Exception as e:
        print(f"Test setup incomplete: {e}")
        print("\\nManual setup required:")
        print("  1. Create Google Sheets calculator using structure above")
        print("  2. Update Sheet ID: 1Qa35rPUURaPki4fCjX23lRzoezeFdNoOOgaDBAMhWXE")
        print("  3. Test the calculator manually before integration")

def validate_config():
    """Validate the timber strength config file."""
    print("\\nVALIDATING CONFIG FILE")
    print("=" * 30)
    
    config_path = Path(__file__).parent / "configs" / "calculators" / "timber_strength.json"
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print("Config file created successfully:")
        print(f"   Name: {config['name']}")
        print(f"   Title: {config['title']}")
        print(f"   Standard: {config['standard']}")
        print(f"   Sheet ID: {config['sheet_id']}")
        print(f"   Inputs: {len(config['inputs'])} parameters")
        print(f"   Outputs: {len(config['outputs'])} results")
    else:
        print("Config file not found")

if __name__ == "__main__":
    print_sheets_structure()
    validate_config()
    test_timber_calculator()