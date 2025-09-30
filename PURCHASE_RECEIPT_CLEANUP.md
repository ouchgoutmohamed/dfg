## SDRT Purchase Receipt - Standard ERPNext Flow

All Purchase Receipt customizations have been removed to ensure compatibility with standard ERPNext behavior.

### Current Flow

1. **SDR Budget** → automatically creates **Item** (item_code = code_analytique)
2. **Purchase Order** → uses the budget Item codes (validated server-side)  
3. **Purchase Receipt** → uses standard ERPNext "Get Items from Purchase Order" functionality

### Testing Steps

1. Create a Purchase Receipt
2. Select a Supplier first 
3. Click "Get Items From" > "Purchase Order"
4. Select a Purchase Order with budget items
5. Verify items are mapped correctly with proper item codes (not "1")

### What Was Removed

- All custom Purchase Receipt JavaScript code
- All custom Purchase Receipt server-side validation hooks  
- Custom PO→PR mapping override
- Any Purchase Receipt-specific customizations

### What Remains

- Purchase Order budget item validation (ensures real Item codes)
- SDR Budget auto-creates Items on insert
- Material Request custom child table support
- Purchase Order budget commitment tracking

This keeps the solution minimal and maintains full ERPNext compatibility.