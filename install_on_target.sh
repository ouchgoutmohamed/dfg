#!/bin/bash
# SDRT App Installation Script for Target Computer
# Run this script on the target computer after extracting sdrt-app.tar.gz

set -e  # Exit on any error

echo "=== SDRT App Installation Script ==="
echo "Installing SDRT app in Frappe environment..."

# Check if we're in a frappe-bench directory
if [ ! -f "sites/apps.txt" ]; then
    echo "❌ Error: This doesn't appear to be a frappe-bench directory"
    echo "Please run this script from your frappe-bench folder"
    exit 1
fi

# Check if sdrt directory exists
if [ ! -d "sdrt" ]; then
    echo "❌ Error: sdrt directory not found"
    echo "Please ensure you've extracted the sdrt-app.tar.gz file in the current directory"
    exit 1
fi

# Get site name
if [ -z "$1" ]; then
    echo "Please provide the site name as an argument:"
    echo "Usage: $0 your-site-name"
    exit 1
fi

SITE_NAME=$1

# Validate site exists
if [ ! -d "sites/$SITE_NAME" ]; then
    echo "❌ Error: Site '$SITE_NAME' not found"
    echo "Available sites:"
    ls -1 sites/ | grep -v assets | grep -v apps.txt | grep -v common_site_config.json
    exit 1
fi

echo "Installing SDRT app for site: $SITE_NAME"

# Step 1: Move app to apps directory if not already there
if [ ! -d "apps/sdrt" ]; then
    echo "📁 Moving sdrt to apps directory..."
    mv sdrt apps/
else
    echo "📁 SDRT app already in apps directory"
fi

# Step 2: Add app to apps.txt if not already there
echo "📋 Adding app to apps.txt..."
if ! grep -q "^sdrt$" sites/apps.txt; then
    echo "sdrt" >> sites/apps.txt
    echo "✓ Added sdrt to apps.txt"
else
    echo "✓ sdrt already in apps.txt"
fi

# Step 3: Get the app (this registers it with bench)
echo "📋 Registering app with bench..."
# Use absolute path to avoid issues
APP_PATH=$(pwd)/apps/sdrt
bench get-app "$APP_PATH" || echo "⚠️  App may already be registered"

# Step 4: Install the app on the site
echo "🔧 Installing app on site $SITE_NAME..."
bench --site $SITE_NAME install-app sdrt

# Step 5: Clear cache and build the app
echo "🧹 Clearing cache..."
bench --site $SITE_NAME clear-cache

echo "🏗️  Building app assets..."
bench build --app sdrt

# Step 6: Run migrations
echo "🔄 Running migrations..."
bench --site $SITE_NAME migrate

# Step 7: Restart services
echo "🔄 Restarting services..."
bench restart

# Step 8: Verify installation
echo "🔍 Verifying installation..."
if bench --site $SITE_NAME list-apps | grep -q "sdrt"; then
    echo "✅ SDRT App installation completed successfully!"
    echo "🌐 You can now access your site at: http://your-domain:8000"
    echo ""
    echo "🎉 Installation Summary:"
    echo "   ✓ App registered with bench"
    echo "   ✓ Installed on site: $SITE_NAME"
    echo "   ✓ Assets built successfully"
    echo "   ✓ Migrations completed"
    echo "   ✓ Services restarted"
else
    echo "⚠️  Installation may have issues. Please check manually:"
    echo "   bench --site $SITE_NAME list-apps"
fi
echo ""
echo "🔧 If you encounter any issues, try:"
echo "   bench clear-cache"
echo "   bench build"
echo "   bench restart"