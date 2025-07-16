#!/usr/bin/env python3
"""
Set up the timber strength calculator in Google Sheets.
This script will create the complete calculator structure with all formulas.
"""

import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes for Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID of your spreadsheet
SPREADSHEET_ID = '1Qa35rPUURaPki4fCjX23lRzoezeFdNoOOgaDBAMhWXE'

def get_sheets_service():
    """Get authenticated Google Sheets service using service account."""
    # Path to your service account key file
    SERVICE_ACCOUNT_FILE = 'credentials/service_account.json'
    
    # Create credentials from service account
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    
    # Build the sheets service
    return build('sheets', 'v4', credentials=creds)

def setup_timber_calculator():
    """Set up the complete timber calculator in the spreadsheet."""
    service = get_sheets_service()
    
    # Clear existing content first
    clear_request = {
        'ranges': ['A1:Z100']
    }
    service.spreadsheets().values().batchClear(
        spreadsheetId=SPREADSHEET_ID,
        body=clear_request
    ).execute()
    
    # Define all the data to write
    data = [
        # Headers and titles
        {
            'range': 'A1:D1',
            'values': [['AS 1720.1 TIMBER BEAM DESIGN CALCULATOR', '', '', '']]
        },
        # Input labels and values
        {
            'range': 'A2:D12',
            'values': [
                ['INPUTS', '', '', ''],
                ['Beam Width (mm):', 90, '', 'Cross-section width'],
                ['Beam Depth (mm):', 190, '', 'Cross-section depth'],
                ['f\'b (MPa):', 42, '', 'Characteristic bending strength (see F-grades below)'],
                ['Application Category:', 1, '', '1=House, 2=Commercial, 3=Industrial'],
                ['Load Duration (years):', 50, '', '0=5 seconds, 0.014=5 days, 0.42=5 months, 50=50+ years'],
                ['k4 Factor:', 1.0, '', 'Partial seasoning factor (1.0 for fully seasoned)'],
                ['k6 Factor:', 1.0, '', 'Temperature factor (1.0 for normal conditions)'],
                ['k9 Factor:', 1.0, '', 'Strength sharing factor (1.0 for single member)'],
                ['k12 Stability Factor:', 1.0, '', 'Stability factor (1.0 for adequately restrained)'],
                ['Applied Moment M* (kN.m):', 10, '', 'Enter your design moment here']
            ]
        },
        # Output labels
        {
            'range': 'A14:D20',
            'values': [
                ['OUTPUTS', '', '', ''],
                ['Section Modulus Z (mm³):', '', '', 'Z = bd²/6'],
                ['Capacity Factor φ:', '', '', 'Based on application category'],
                ['Duration Factor k1:', '', '', 'Based on load duration'],
                ['Design Capacity Md (kN.m):', '', '', 'Md = φ×k1×k4×k6×k9×k12×f\'b×Z'],
                ['Utilization Ratio:', '', '', 'M*/Md'],
                ['Beam Assessment:', '', '', 'Pass/Fail check']
            ]
        },
        # F-grade reference table
        {
            'range': 'A22:C32',
            'values': [
                ['F-GRADE REFERENCE TABLE (AS 1720.1 Table H2.1)', '', ''],
                ['Grade', 'f\'b (MPa)', 'E (MPa)'],
                ['F34', 84, 21500],
                ['F27', 67, 18500],
                ['F22', 55, 16000],
                ['F17', 42, 14000],
                ['F14', 36, 12000],
                ['F11', 31, 10500],
                ['F8', 22, 9100],
                ['F7', 18, 7900],
                ['F5', 14, 6900]
            ]
        }
    ]
    
    # Write all the data
    body = {
        'valueInputOption': 'USER_ENTERED',
        'data': data
    }
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body=body
    ).execute()
    
    # Now add the formulas
    formulas = [
        {
            'range': 'B15',  # Section Modulus
            'values': [['=B3*B4^2/6']]
        },
        {
            'range': 'B16',  # Capacity Factor
            'values': [['=IF(B6=1,0.95,IF(B6=2,0.85,0.75))']]
        },
        {
            'range': 'B17',  # Duration Factor k1
            'values': [['=IF(B7>=50,0.57,IF(B7>=0.42,0.8,IF(B7>=0.014,0.94,1)))']]
        },
        {
            'range': 'B18',  # Design Capacity Md in kN.m
            'values': [['=B16*B17*B8*B9*B10*B11*B5*B15/1000000']]
        },
        {
            'range': 'B19',  # Utilization Ratio
            'values': [['=B12/B18']]
        },
        {
            'range': 'B20',  # Beam Assessment
            'values': [['=IF(B19<=1,"ADEQUATE - Beam passes design check","INADEQUATE - Increase beam size or grade")']]
        }
    ]
    
    # Write formulas
    formula_body = {
        'valueInputOption': 'USER_ENTERED',
        'data': formulas
    }
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body=formula_body
    ).execute()
    
    # Format the spreadsheet
    formatting_requests = [
        # Make title bold and larger
        {
            'mergeCells': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': 4
                },
                'mergeType': 'MERGE_ALL'
            }
        },
        {
            'repeatCell': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': 4
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.6},
                        'textFormat': {
                            'fontSize': 16,
                            'bold': True,
                            'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}
                        },
                        'horizontalAlignment': 'CENTER'
                    }
                },
                'fields': 'userEnteredFormat'
            }
        },
        # Format section headers
        {
            'repeatCell': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 2,
                    'endRowIndex': 3,
                    'startColumnIndex': 0,
                    'endColumnIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {'bold': True},
                        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                    }
                },
                'fields': 'userEnteredFormat'
            }
        },
        {
            'repeatCell': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 14,
                    'endRowIndex': 15,
                    'startColumnIndex': 0,
                    'endColumnIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {'bold': True},
                        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                    }
                },
                'fields': 'userEnteredFormat'
            }
        },
        # Format input cells with light blue background
        {
            'repeatCell': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 3,
                    'endRowIndex': 13,
                    'startColumnIndex': 1,
                    'endColumnIndex': 2
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.9, 'green': 0.95, 'blue': 1}
                    }
                },
                'fields': 'userEnteredFormat.backgroundColor'
            }
        },
        # Format output cells with light green background
        {
            'repeatCell': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 15,
                    'endRowIndex': 21,
                    'startColumnIndex': 1,
                    'endColumnIndex': 2
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.9, 'green': 1, 'blue': 0.9}
                    }
                },
                'fields': 'userEnteredFormat.backgroundColor'
            }
        },
        # Set column widths
        {
            'updateDimensionProperties': {
                'range': {
                    'sheetId': 0,
                    'dimension': 'COLUMNS',
                    'startIndex': 0,
                    'endIndex': 1
                },
                'properties': {
                    'pixelSize': 200
                },
                'fields': 'pixelSize'
            }
        },
        {
            'updateDimensionProperties': {
                'range': {
                    'sheetId': 0,
                    'dimension': 'COLUMNS',
                    'startIndex': 1,
                    'endIndex': 2
                },
                'properties': {
                    'pixelSize': 120
                },
                'fields': 'pixelSize'
            }
        },
        {
            'updateDimensionProperties': {
                'range': {
                    'sheetId': 0,
                    'dimension': 'COLUMNS',
                    'startIndex': 3,
                    'endIndex': 4
                },
                'properties': {
                    'pixelSize': 400
                },
                'fields': 'pixelSize'
            }
        }
    ]
    
    # Apply formatting
    format_body = {
        'requests': formatting_requests
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body=format_body
    ).execute()
    
    print("AS 1720.1 TIMBER BEAM CALCULATOR SETUP COMPLETE!")
    print("=" * 60)
    print(f"\nSpreadsheet URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    print("\nThe calculator is now ready to use with:")
    print("- All input fields configured")
    print("- Formulas for AS 1720.1 calculations")
    print("- F-grade reference table")
    print("- Automatic beam assessment")
    print("\nDefault values show an F17 90x190mm beam example.")
    print("Adjust the inputs to match your specific design requirements.")

if __name__ == "__main__":
    try:
        setup_timber_calculator()
    except HttpError as error:
        print(f"An error occurred: {error}")
        print("\nTroubleshooting:")
        print("1. Make sure you have credentials.json in the backend directory")
        print("2. Ensure you have edit access to the spreadsheet")
        print("3. Check that the Google Sheets API is enabled in your Google Cloud project")