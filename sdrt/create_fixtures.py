import frappe
import json
import os
from frappe.utils import get_bench_path

def create_fixtures():  # ← Changed function name
    """Create fixture files for your custom app"""
    app_name = 'sdrt'  # ← Added app_name variable
    bench_path = get_bench_path()
    app_path = os.path.join(bench_path, 'apps', app_name, app_name, 'fixtures')
    
    # Create fixtures directory if it doesn't exist
    os.makedirs(app_path, exist_ok=True)
    
    fixtures_created = []
    
    # Define fixture creation functions for each doctype
    doctype_configs = [
        {
            'doctype': 'Custom Field',
            'filters': {},
            'fields': ['*'],
            'order_by': 'dt'
        },
        {
            'doctype': 'Property Setter', 
            'filters': {},
            'fields': ['*'],
            'order_by': 'doc_type'
        },
        {
            'doctype': 'Client Script',
            'filters': {},
            'fields': ['*'],
            'order_by': 'dt'
        },
        {
            'doctype': 'Print Format',
            'filters': {'standard': 0},
            'fields': ['*'],
            'order_by': 'doc_type'
        },
        {
            'doctype': 'Workflow',
            'filters': {},
            'fields': ['*'],
            'order_by': 'document_type'
        },
        {
            'doctype': 'Report',
            'filters': {'is_standard': 'No'},
            'fields': ['*'],
            'order_by': 'ref_doctype'
        },
        {
            'doctype': 'Server Script',
            'filters': {},
            'fields': ['*'],
            'order_by': 'doctype_event'
        },
        {
            'doctype': 'Workspace',
            'filters': {'is_standard': 0},
            'fields': ['*'],
            'order_by': 'label'
        }
    ]
    
    for config in doctype_configs:
        filename = config['doctype'].lower().replace(' ', '_') + '.json'
        filepath = os.path.join(app_path, filename)
        
        records = frappe.get_all(
            config['doctype'],
            filters=config['filters'],
            fields=config['fields'],
            order_by=config['order_by']
        )
        
        if records:
            # Convert to proper fixture format
            fixture_data = []
            for record in records:
                # Remove internal fields that shouldn't be in fixtures
                record.pop('creation', None)
                record.pop('modified', None)
                record.pop('modified_by', None)
                record.pop('owner', None)
                
                fixture_data.append(record)
            
            with open(filepath, 'w') as f:
                json.dump(fixture_data, f, indent=2, default=str)
            
            fixtures_created.append(f"{config['doctype']} ({len(records)} records)")
            print(f"✅ Created {filename} with {len(records)} records")
        else:
            print(f"⏭️  No records found for {config['doctype']}")
    
    return fixtures_created

# Hooks.py configuration for your app
HOOKS_EXAMPLE = """
# Add this to your app's hooks.py
fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "SDRT"]]},
    {"dt": "Property Setter", "filters": [["module", "=", "SDRT"]]},
    {"dt": "Client Script", "filters": [["module", "=", "SDRT"]]},
    {"dt": "Print Format", "filters": [["standard", "=", 0], ["module", "=", "SDRT"]]},
    {"dt": "Workflow", "filters": [["module", "=", "SDRT"]]},
    {"dt": "Report", "filters": [["is_standard", "=", "No"], ["module", "=", "SDRT"]]},
    {"dt": "Server Script", "filters": [["module", "=", "SDRT"]]},
    {"dt": "Workspace", "filters": [["is_standard", "=", 0], ["module", "=", "SDRT"]]}
]
"""

# Execute the creation
if __name__ == "__main__":
    created = create_fixtures()  # ← Changed function call
    
    print(f"\n🎉 Created {len(created)} fixture files:")
    for fixture in created:
        print(f"   - {fixture}")
    
    print(f"\n📁 Fixtures saved to: {os.path.join(get_bench_path(), 'apps', 'sdrt', 'sdrt', 'fixtures')}")
    print("\n📋 Add this to your hooks.py:")
    print(HOOKS_EXAMPLE)