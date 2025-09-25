#!/bin/bash
# SDRT App Validation Script
# Run this before packaging to ensure all required files are present

echo "=== SDRT App Validation Script ==="
echo "Checking app structure and required files..."

APP_DIR="/home/ouchg/frappe-bench/apps/sdrt"
cd "$APP_DIR"

# Check critical files
FILES_TO_CHECK=(
    "pyproject.toml"
    "README.md"
    "license.txt"
    "sdrt/__init__.py"
    "sdrt/hooks.py"
    "sdrt/modules.txt"
    "sdrt/patches.txt"
)

echo "📋 Checking required files:"
MISSING_FILES=0
for file in "${FILES_TO_CHECK[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file (MISSING)"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

# Check if __version__ is properly defined
echo ""
echo "🔍 Checking version configuration:"
if grep -q "__version__" sdrt/__init__.py; then
    VERSION=$(python3 -c "import sys; sys.path.insert(0, '.'); from sdrt import __version__; print(__version__)")
    echo "✅ Version: $VERSION"
else
    echo "❌ __version__ not found in sdrt/__init__.py"
    MISSING_FILES=$((MISSING_FILES + 1))
fi

# Check hooks.py structure
echo ""
echo "🔍 Checking hooks.py configuration:"
REQUIRED_HOOKS=(
    "app_name"
    "app_title"
    "app_publisher"
    "app_description"
    "app_email"
    "app_license"
)

for hook in "${REQUIRED_HOOKS[@]}"; do
    if grep -q "^$hook" sdrt/hooks.py; then
        VALUE=$(grep "^$hook" sdrt/hooks.py | cut -d'=' -f2 | tr -d ' "')
        echo "✅ $hook = $VALUE"
    else
        echo "❌ $hook (MISSING from hooks.py)"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

# Check modules.txt
echo ""
echo "🔍 Checking modules.txt:"
if [ -s "sdrt/modules.txt" ]; then
    echo "✅ modules.txt contains: $(cat sdrt/modules.txt)"
else
    echo "❌ modules.txt is empty or missing"
    MISSING_FILES=$((MISSING_FILES + 1))
fi

# Check doctype structure
echo ""
echo "🔍 Checking doctype structure:"
DOCTYPE_COUNT=$(find sdrt/sdrt/doctype -name "*.json" | wc -l)
echo "✅ Found $DOCTYPE_COUNT doctypes"

if [ $DOCTYPE_COUNT -gt 0 ]; then
    echo "📄 Doctypes found:"
    find sdrt/sdrt/doctype -name "*.json" | head -5 | while read file; do
        doctype_name=$(basename "$(dirname "$file")")
        echo "   - $doctype_name"
    done
    if [ $DOCTYPE_COUNT -gt 5 ]; then
        echo "   ... and $((DOCTYPE_COUNT - 5)) more"
    fi
fi

# Check pyproject.toml structure
echo ""
echo "🔍 Checking pyproject.toml:"
if python3 -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))" 2>/dev/null; then
    echo "✅ pyproject.toml is valid TOML"
else
    echo "❌ pyproject.toml has syntax errors"
    MISSING_FILES=$((MISSING_FILES + 1))
fi

# Final summary
echo ""
echo "==============================================="
if [ $MISSING_FILES -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED!"
    echo "🎉 Your SDRT app is ready for packaging and distribution."
    echo ""
    echo "Next steps:"
    echo "1. Run: ./package_enhanced.sh"
    echo "2. Transfer sdrt-app-complete.tar.gz to target computer"
    echo "3. Run installation script on target"
else
    echo "❌ VALIDATION FAILED!"
    echo "🔧 Found $MISSING_FILES issues that need to be fixed before packaging."
    echo ""
    echo "Please fix the missing/incorrect files and run this script again."
fi
echo "==============================================="